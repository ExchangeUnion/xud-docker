from __future__ import annotations

import datetime
import itertools
import logging
import os
from threading import Event
from typing import List, Dict, Any, Optional, Tuple
from typing import TYPE_CHECKING

import docker
from docker import DockerClient
from docker.errors import NotFound
from docker.models.containers import Container

from launcher.config import PortPublish
from .image import Image
from .pty import exec_command

if TYPE_CHECKING:
    from launcher.config import Config
    from .image import ImageManager
    from . import NodeManager

logger = logging.getLogger(__name__)


class InvalidNetwork(Exception):
    def __init__(self, network):
        super().__init__(network)
        self.network = network


class ContainerNotFound(Exception):
    pass


class ContainerSpec:
    def __init__(self, name: str, image: Image, hostname: str, environment: List[str], command: List[str],
                 volumes: Dict, ports: Dict):
        self.name = name
        self.image = image
        self.hostname = hostname
        self.environment = environment
        self.command = command
        self.volumes = volumes
        self.ports = ports


class OutputStream:
    def __init__(self, fd):
        self.fd = fd

    def isatty(self) -> bool:
        return True

    def fileno(self) -> int:
        return self.fd


def diff_details(s1, s2):
    d1 = s1 - s2
    d2 = s2 - s1
    lines = []
    for item in d1:
        lines.append("D %s" % item)
    for item in d2:
        lines.append("A %s" % item)
    return "\n".join(lines)


class Node:
    client: DockerClient
    config: Config
    image_manager: ImageManager
    node_manager: NodeManager
    name: str
    container_spec: ContainerSpec

    _container: Optional[Container]
    _image_status: Optional[str]
    _container_status: Optional[str]
    _logger: logging.Logger
    _cli: Any

    def __init__(self, name: str, ctx):
        self.client = docker.from_env(timeout=999999999)
        self.config = ctx.config
        self.image_manager = ctx.image_manager
        self.node_manager = ctx.node_manager

        self.name = name

        self.container_spec = ContainerSpec(
            name=self.container_name,
            image=self.image,
            hostname=self.name,
            environment=self.generate_environment(),
            command=[],
            volumes=self.generate_volumes(),
            ports=self.generate_ports(),
        )
        self._container = None

        # used for updates
        self._image_status = None
        self._container_status = None

        self._logger = logger

        self._cli = None

    def __repr__(self):
        return "<Service %s>" % self.name

    def generate_environment(self):
        environment = [f"NETWORK={self.network}"]
        if self.node_config["preserve_config"]:
            environment.append("PRESERVE_CONFIG=true")
        else:
            environment.append("PRESERVE_CONFIG=false")
        return environment

    def generate_volumes(self):
        volumes = {}
        for v in self.node_config["volumes"]:
            volumes[v["host"]] = {
                "bind": v["container"],
                "mode": "rw"
            }
        return volumes

    def generate_ports(self):
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
    def network(self) -> str:
        return self.config.network

    @property
    def network_name(self) -> str:
        return self.network + "_default"

    @property
    def node_config(self) -> Dict:
        return self.config.nodes[self.name]

    @property
    def image(self) -> Image:
        return self.image_manager.get_image(self.node_config["image"], self)

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

    @property
    def data_dir(self) -> str:
        return os.path.join(self.config.data_dir, self.name)

    def get_service(self, name) -> Node:
        return self.node_manager.get_service(name)

    def _get_ports(self, spec_ports: Dict):
        ports = []
        for key, value in spec_ports.items():
            if "/" in key:
                parts = key.split("/")
                ports.append((int(parts[0]), parts[1]))
            else:
                ports.append((int(key)))
        return ports

    def _get_volumes(self, spec_volumes: Dict):
        volumes = []
        for key, value in spec_volumes.items():
            volumes.append(value["bind"])
        return volumes

    def create(self):
        spec = self.container_spec
        api = self.client.api

        image = spec.image.use_image

        logger.debug("Creating container %s with image %s", self.container_name, image)

        resp = api.create_container(
            image=image,
            command=spec.command,
            hostname=spec.hostname,
            detach=True,
            ports=self._get_ports(spec.ports),
            environment=spec.environment,
            volumes=self._get_volumes(spec.volumes),
            name=spec.name,
            host_config=api.create_host_config(
                port_bindings=spec.ports,
                binds=spec.volumes,
                # cpu_quota=10000,
            ),
            networking_config=api.create_networking_config({
                self.network_name: api.create_endpoint_config(
                    aliases=[self.name]
                )
            }),
        )
        id = resp['Id']
        container = self.client.containers.get(id)
        return container

    @property
    def container(self) -> Container:
        try:
            return self.client.containers.get(self.container_name)
        except docker.errors.NotFound as e:
            raise ContainerNotFound(self.name) from e

    def start(self) -> None:
        if self.mode != "native":
            return
        self.container.start()

    def stop(self, timeout=180) -> None:
        if self.mode != "native":
            return
        self.container.stop(timeout=timeout)

    def remove(self, force=False) -> None:
        if self.mode != "native":
            return
        self.container.remove(force=force)

    @property
    def is_running(self) -> bool:
        return self.container.status == "running"

    def status(self) -> str:
        try:
            return "Container " + self.container.status
        except ContainerNotFound:
            return "Container missing"

    def exec(self, command: str) -> Tuple[int, str]:
        exit_code, output = self.container.exec_run(command)
        return exit_code, output.decode()

    def cli(self, command: str, exception=False, parse_output=None) -> None:
        if self.mode != "native":
            return

        try:
            full_cmd = "%s %s" % (self._cli, command)
            logger.debug("[Execute] %s (interactive)", full_cmd)
            # FIXME use blocking docker client here
            output = exec_command(self.client.api, self.container_name, full_cmd)
            try:
                self.extract_exception(command, output)
            except KeyboardInterrupt:
                raise
            except:
                if exception:
                    raise
            if parse_output:
                parse_output(output)
        except docker.errors.NotFound:
            # FIXME use self.container
            raise ContainerNotFound(self.name)

    def extract_exception(self, cmd, text):
        pass

    def cli_filter(self, cmd, text):
        return text

    def _get_container_created_timestamp(self):
        created = self._container.attrs["Created"]  # 2019-12-20T18:20:41.646406053
        parts = created.split('.')
        t = datetime.datetime.strptime(parts[0], "%Y-%m-%dT%H:%M:%S")
        return t

    def logs(self, tail: str = None, since: str = None, until: str = None, follow: bool = False, timestamps: bool = False):
        assert since is None, "String since is not supported yet"
        assert until is None, "String until is not supported yet"
        try:
            tail = int(tail)
        except:
            pass

        kwargs = {
            "tail": tail,
            "follow": follow,
            "timestamps": timestamps,
        }

        if follow:
            kwargs["stream"] = True

        result = self.container.logs(**kwargs)
        if isinstance(result, bytes):
            for line in result.decode().splitlines():
                yield line
        else:
            for line in result:
                yield line.decode().rstrip()

    def _compare_image(self, container: Container) -> bool:
        attrs = container.attrs

        old_name = attrs["Config"]["Image"]
        new_name = self.image.use_image

        if old_name != new_name:
            logger.info("(%s) Image %s -> %s", self.container_name, old_name, new_name)
            return False

        if self.image.pull_image:
            # the names are the same but new image available on registry
            logger.info("(%s) Image pulling required", self.container_name)
            return False

        old_digest = attrs["Image"]
        new_digest = self.image.digest

        if old_digest != new_digest:
            # the names are the same and no image needs to be pulled but image
            # digests are different
            logger.info("(%s) Image (digest) %s -> %s", self.container_name, old_digest, new_digest)
            return False

        return True

    def _compare_env(self, container: Container) -> bool:

        old_env = []

        ignore = [
            "NODE_VERSION",
            "YARN_VERSION",
            "PATH",
        ]

        attrs = container.attrs
        env = attrs["Config"]["Env"]

        def ignored(item):
            for key in ignore:
                if item.startswith(key):
                    return True
            return False

        if env:
            for item in env:
                if ignored(item):
                    continue
                old_env.append(item)

        new_env = self.container_spec.environment

        old_set = set(old_env)
        new_set = set(new_env)

        if old_set != new_set:
            logger.info("(%s) Environment\n%s", self.container_name, diff_details(old_set, new_set))
            return False

        return True

    def _compare_command(self, container: Container) -> bool:
        attrs = container.attrs
        old_command = attrs["Config"]["Cmd"]
        new_command = self.container_spec.command

        if not old_command:
            old_command = []

        old_set = set(old_command)
        new_set = set(new_command)

        if old_set != new_set:
            logger.info("(%s) Command\n%s", self.container_name, diff_details(old_set, new_set))
            return False

        return True

    def _compare_volumes(self, container: Container) -> bool:
        attrs = container.attrs
        old_volumes = ["{}:{}:{}".format(m["Source"], m["Destination"], m["Mode"]) for m in attrs["Mounts"]]

        # macOS workaround
        old_volumes = [v.replace("/host_mnt", "") for v in old_volumes]

        new_volumes = ["{}:{}:{}".format(key, value["bind"], value["mode"]) for key, value in
                       self.container_spec.volumes.items()]

        old_set = set(old_volumes)
        new_set = set(new_volumes)

        if old_set != new_set:
            logger.info("(%s) Volumes\n%s", self.container_name, diff_details(old_set, new_set))
            return False

        return True

    def _normalize_docker_port_bindings(self, port_bindings):
        result = []
        for key, value in port_bindings.items():
            if value:
                mapping = []
                for p in value:
                    host_ip = p["HostIp"]
                    if host_ip == "":
                        host_ip = "0.0.0.0"
                    host_port = p["HostPort"]
                    mapping.append(host_ip + ":" + host_port)
                result.append(key + "-" + ",".join(mapping))
        return result

    def _compare_ports(self, container: Container) -> bool:
        attrs = container.attrs
        port_bindings = attrs["HostConfig"]["PortBindings"]
        old_ports = self._normalize_docker_port_bindings(port_bindings)

        def normalize(value):
            if isinstance(value, int):
                return "0.0.0.0:{}".format(value)
            elif isinstance(value, tuple):
                if len(value) != 2:
                    raise RuntimeError("container_spec ports value tuple should contain 2 elements: {}".format(value))
                return "{}:{}".format(value[0], value[1])
            else:
                raise RuntimeError("Unexpected container_spec ports value: {}".format(value))

        new_ports = [key + "-" + normalize(value) for key, value in self.container_spec.ports.items()]

        old_set = set(old_ports)
        new_set = set(new_ports)

        if old_set != new_set:
            logger.info("%s: Ports\n%s", self.container_name, diff_details(old_set, new_set))
            return False

        return True

    def _same(self, container: Container) -> bool:
        return self._compare_image(container) \
               and self._compare_env(container) \
               and self._compare_command(container) \
               and self._compare_volumes(container) \
               and self._compare_ports(container)

    def _update_action(self) -> str:
        try:
            container = self.client.containers.get(self.container_name)

            if self.mode != "native":
                return "REMOVE"  # external

            if self.disabled:
                return "REMOVE"  # disabled

            if self._same(container):
                return "NONE"
            else:
                return "RECREATE"

        except NotFound:
            if self.mode != "native":
                return "NONE"
            if self.disabled:
                return "NONE"
            return "CREATE"

    def get_update_action(self) -> str:
        action = self._update_action()
        logger.info("Container %s: action=%s", self.container_name, action)
        return action

    def ensure_ready(self, stop: Event) -> None:
        pass


class CliError(Exception):
    def __init__(self, exit_code, output):
        super().__init__(f"{exit_code}|{output!r}")
        self.exit_code = exit_code
        self.output = output


class CliBackend:
    def __init__(self, name, container_name, cli):
        self.name = name
        self.container_name = container_name
        self.cli = cli

        self.client = docker.from_env()
        self.blocking_client = docker.from_env(timeout=9999999)

    def get_container(self, blocking=False):
        try:
            if blocking:
                return self.blocking_client.containers.get(self.container_name)
            else:
                return self.client.containers.get(self.container_name)
        except docker.errors.NotFound as e:
            raise ContainerNotFound() from e

    def invoke(self, method, *args):
        if len(args) > 0:
            cmd = "%s %s" % (method, " ".join(args))
        else:
            cmd = method
        full_cmd = "%s %s" % (self.cli, cmd)
        if cmd.startswith("create") or cmd.startswith("restore"):
            exit_code, output = self.get_container(blocking=True).exec_run(full_cmd)
        else:
            exit_code, output = self.get_container().exec_run(full_cmd)

        text = output.decode().rstrip()

        if exit_code == 0:
            logger.debug("[Execute] %s", full_cmd)
        else:
            logger.debug("[Execute] %s (exit_code=%s)\n%s", full_cmd, exit_code, text)
            raise CliError(exit_code, text)

        return text
