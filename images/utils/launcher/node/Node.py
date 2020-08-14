from __future__ import annotations
import datetime
import itertools
import os
import sys
from typing import List, Dict, Optional, TYPE_CHECKING, Generic, TypeVar, get_args
from abc import ABC, abstractmethod
import logging
from dataclasses import dataclass

from docker import DockerClient
from docker.errors import NotFound
from docker.models.containers import Container

from launcher.config import PortPublish

if TYPE_CHECKING:
    from launcher.config import Config
    from .NodeManager import NodeManager, Context
    from .docker import DockerTemplate


__all__ = ["Node", "NodeApi"]


class InvalidNetwork(Exception):
    def __init__(self, network):
        super().__init__(network)
        self.network = network


@dataclass
class ContainerSpec:
    name: str
    image: str
    hostname: str
    environment: List[str]
    command: List[str]
    volumes: Dict
    ports: Dict


class CliError(Exception):
    def __init__(self, command: str, exit_code: int, output: str):
        super().__init__("Command '%s' returned non-zero exit status %d" % (command, exit_code))
        self.command = command
        self.exit_code = exit_code
        self.output = output


class NodeApi:
    def __init__(self, node: Node):
        self.node = node

    def cli(self, command) -> str:
        full_cmd = "%s %s" % (self.node.cli_prefix, command)
        exit_code, output = self.node.exec(full_cmd)
        output = output.decode().strip()
        if exit_code != 0:
            raise CliError(full_cmd, exit_code, output)
        return output


T = TypeVar('T', bound=NodeApi)


class ContainerNotFound(Exception):
    pass


class Node(ABC, Generic[T]):
    api: T

    def __init__(self, name: str, context: Context):
        self.context = context
        self.name = name
        self.logger = logging.getLogger("launcher.node." + name.capitalize())

        self.container_spec = ContainerSpec(
            name=self.container_name,
            image=self.image,
            hostname=self.name,
            environment=self._get_environment(),
            command=[],
            volumes=self._get_volumes(),
            ports=self._get_ports(),
        )
        self.api = self._create_api()

    def _create_api(self) -> Optional[T]:
        args = get_args(self.__class__.__orig_bases__[0])
        if len(args) == 0:
            return None
        return args[0](self)

    @property
    def cli_prefix(self) -> Optional[str]:
        return None

    def _get_environment(self):
        environment = [f"NETWORK={self.network}"]
        if self.node_config["preserve_config"]:
            environment.append("PRESERVE_CONFIG=true")
        else:
            environment.append("PRESERVE_CONFIG=false")
        return environment

    def _get_volumes(self):
        volumes = {}
        for v in self.node_config["volumes"]:
            volumes[v["host"]] = {
                "bind": v["container"],
                "mode": "rw"
            }
        return volumes

    def _get_ports(self):
        ports = {}
        for p in self.node_config["ports"]:
            if not isinstance(p, PortPublish):
                raise RuntimeError("node_config ports must contain PortPublish instances")
            if p.host:
                ports[f"{p.port}/{p.protocol}"] = (p.host, p.host_port)
            else:
                ports[f"{p.port}/{p.protocol}"] = p.host_port
        return ports

    @property
    def config(self) -> Config:
        return self.context.config

    @property
    def client(self) -> DockerClient:
        return self.context.docker_client_factory.shared_client

    @property
    def node_manager(self) -> NodeManager:
        return self.context.node_manager

    @property
    def docker_template(self) -> DockerTemplate:
        return self.context.docker_template

    @property
    def network(self) -> str:
        return self.config.network

    @property
    def network_name(self) -> str:
        return self.network + "_default"

    @property
    def node_config(self) -> Dict:
        return self.config.nodes[self.name]

    @property
    def image(self) -> str:
        name = self.node_config["image"]
        if self.config.branch == "master":
            return name
        branch_image = self.docker_template.get_branch_image_name(name, self.config.branch)
        if self.config.dev_mode:
            if self.docker_template.has_local_image(branch_image):
                return branch_image
        if self.docker_template.has_registry_image(branch_image):
            return branch_image
        else:
            return name

    @property
    def mode(self) -> str:
        return self.node_config["mode"]

    @property
    def container_name(self) -> str:
        return f"{self.network}_{self.name}_1"

    @property
    def disabled(self) -> bool:
        result = False
        if "disabled" in self.node_config:
            result = self.node_config["disabled"]
        return result

    def _convert_ports(self, spec_ports: Dict):
        ports = []
        for key, value in spec_ports.items():
            if "/" in key:
                parts = key.split("/")
                ports.append((int(parts[0]), parts[1]))
            else:
                ports.append((int(key)))
        return ports

    def _convert_volumes(self, spec_volumes: Dict):
        volumes = []
        for key, value in spec_volumes.items():
            volumes.append(value["bind"])
        return volumes

    @property
    def container(self) -> Container:
        try:
            return self.client.containers.get(self.container_name)
        except NotFound as e:
            raise ContainerNotFound from e

    def start(self):
        if self.mode != "native":
            return
        self.container.start()

    def stop(self):
        if self.mode != "native":
            return
        self.container.stop(timeout=180)

    def remove(self):
        if self.mode != "native":
            return
        self.container.remove()

    def status(self) -> str:
        if self.mode != "native":
            return "Mode %s" % self.mode
        try:
            status = self.container.status
            if status == "running":
                return self.application_status()
            else:
                return "Container %s" % status
        except ContainerNotFound:
            return "Container missing"

    @abstractmethod
    def application_status(self) -> str:
        pass

    def exec(self, cmd):
        return self.container.exec_run(cmd)

    def cli(self, cmd, shell):
        if self.mode != "native":
            return
        if not self.container:
            return
        full_cmd = "%s %s" % (self.cli_prefix, cmd)
        _, socket = self.container.exec_run(full_cmd, stdin=True, tty=True, socket=True)

        shell.redirect_stdin(socket._sock)
        try:
            output = ""
            pre_data = None
            while True:
                data = socket.read(1024)

                if pre_data is not None:
                    data = pre_data + data

                if len(data) == 0:
                    break

                try:
                    text = data.decode()
                    pre_data = None
                except:
                    pre_data = data
                    continue

                text = self.cli_filter(cmd, text)
                output += text

                # Write text in chunks in case trigger BlockingIOError: could not complete without blocking
                # because text is too large to fit the output buffer
                # https://stackoverflow.com/questions/54185874/logging-chokes-on-blockingioerror-write-could-not-complete-without-blocking
                i = 0
                while i < len(text):
                    os.write(sys.stdout.fileno(), text[i: i + 1024].encode())
                    i = i + 1024
                sys.stdout.flush()
        finally:
            shell.stop_redirect_stdin()

        # TODO get exit code here
        exception = self.extract_exception(cmd, output)
        if exception:
            raise exception

    def extract_exception(self, cmd, text):
        return None

    def cli_filter(self, cmd, text):
        return text

    def _get_container_created_timestamp(self):
        created = self.container.attrs["Created"]  # 2019-12-20T18:20:41.646406053
        parts = created.split('.')
        t = datetime.datetime.strptime(parts[0], "%Y-%m-%dT%H:%M:%S")
        return t

    def logs(self, tail="all"):
        if not self.container:
            return None
        t = self._get_container_created_timestamp()
        result = self.container.logs(since=t, tail=tail)
        return itertools.chain(result.decode().splitlines())
