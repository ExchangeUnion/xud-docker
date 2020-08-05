import datetime
import itertools
import logging
import os
import sys
from typing import List, Dict, Any
import docker
from docker import DockerClient
from docker.errors import NotFound
from docker.models.containers import Container

from .image import Image
from ..config import PortPublish
from ..types import XudNetwork


class InvalidNetwork(Exception):
    def __init__(self, network):
        super().__init__(network)
        self.network = network


class ContainerSpec:
    def __init__(self, name: str, image: Image, hostname: str, environment: List[str], command: List[str], volumes: Dict, ports: Dict):
        self.name = name
        self.image = image
        self.hostname = hostname
        self.environment = environment
        self.command = command
        self.volumes = volumes
        self.ports = ports

    def __repr__(self):
        return f"<ContainerSpec {self.name=} {self.image=} {self.hostname=} {self.environment=} {self.command=} {self.volumes=} {self.ports=}>"


class CompareEntity:
    def __init__(self, obj: Any, diff: Any = None):
        self.obj = obj
        self.diff = diff

    def __repr__(self):
        return f"<CompareEntity obj={self.obj} diff={self.diff}>"


class CompareResult:
    def __init__(self, same: bool, message: str, old: CompareEntity, new: CompareEntity):
        self.same = same
        self.message = message
        self.old = old
        self.new = new

    def __repr__(self):
        return f"<CompareDetails same={self.same} message={self.message} old={self.old} new={self.new}>"


class Node:
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

        self._logger = logging.getLogger("launcher.node." + self.name)

        self._cli = None

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
    def network(self) -> XudNetwork:
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

    def create_container(self):
        spec = self.container_spec
        api = self.client.api
        resp = api.create_container(
            image=spec.image.use_image,
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

    def get_container(self, create=False):
        try:
            return self.client.containers.get(self.container_name)
        except NotFound:
            if create:
                return self.create_container()
            else:
                return None

    def start(self):
        if self.mode != "native":
            return
        if self._container is None:
            self._container = self.get_container(create=True)
        assert self._container is not None
        self._container.start()

    def stop(self):
        if self.mode != "native":
            return
        if self._container is not None:
            self._container.stop(timeout=180)

    def remove(self):
        if self.mode != "native":
            return
        if self._container is not None:
            self._container.remove()

    def status(self):
        self._container = self.get_container()
        if self._container is None:
            return "Container missing"
        return self._container.status

    def exec(self, cmd):
        if self._container is not None:
            return self._container.exec_run(cmd)

    def cli(self, cmd, shell):
        if self.mode != "native":
            return
        full_cmd = "%s %s" % (self._cli, cmd)
        self._logger.debug("[Execute] %s", full_cmd)
        _, socket = self._container.exec_run(full_cmd, stdin=True, tty=True, socket=True)

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
        created = self._container.attrs["Created"]  # 2019-12-20T18:20:41.646406053
        parts = created.split('.')
        t = datetime.datetime.strptime(parts[0], "%Y-%m-%dT%H:%M:%S")
        return t

    def logs(self, tail="all"):
        if self._container is None:
            return None
        t = self._get_container_created_timestamp()
        result = self._container.logs(since=t, tail=tail)
        return itertools.chain(result.decode().splitlines())

    def compare_image(self, container: Container) -> CompareResult:
        attrs = container.attrs

        old_name = attrs["Config"]["Image"]
        new_name = self.image.use_image

        old = CompareEntity(old_name)
        new = CompareEntity(new_name)

        if old_name != new_name:
            return CompareResult(False, "Image names are different", old, new)

        if self.image.pull_image:
            # the names are same but a new image needs to be pulled
            if self.image.status == "LOCAL_MISSING":
                msg = "Local image is missing"
            elif self.image.status == "LOCAL_OUTDATED":
                msg = "Local image is outdated"
            else:
                raise RuntimeError("The pull_image should be None with status {}".format(self.image.status))
            return CompareResult(False, msg, old, new)

        old_digest = attrs["Image"]
        new_digest = self.image.digest

        if old_digest != new_digest:
            # the names are same and no image needs to be pulled but image
            # digests are different
            old.diff = old_digest
            new.diff = new_digest
            return CompareResult(False, "Image digests are different", old, new)
        return CompareResult(True, "Images are same", old, new)

    def compare_hostname(self, container: Container) -> CompareResult:
        attrs = container.attrs
        old_hostname = attrs["Config"]["Hostname"]
        new_hostname = self.container_spec.hostname
        old = CompareEntity(old_hostname)
        new = CompareEntity(new_hostname)
        if old_hostname != new_hostname:
            return CompareResult(False, "Hostnames are different", old, new)
        return CompareResult(True, "", old, new)

    def compare_environment(self, container: Container) -> CompareResult:
        attrs = container.attrs
        old_environment = attrs["Config"]["Env"]
        new_environment = self.container_spec.environment

        if not old_environment:
            old_environment = []

        old = CompareEntity(old_environment)
        new = CompareEntity(new_environment)

        old_set = set(old_environment)
        new_set = set(new_environment)

        if old_set != new_set:
            old.diff = old_set - new_set
            new.diff = new_set - old_set
            if len(new.diff) == 0:
                return CompareResult(True, "", old, new)
            else:
                return CompareResult(False, "Environments are different", old, new)

        return CompareResult(True, "", old, new)

    def compare_command(self, container: Container) -> CompareResult:
        attrs = container.attrs
        old_command = attrs["Config"]["Cmd"]
        new_command = self.container_spec.command

        if not old_command:
            old_command = []

        old = CompareEntity(old_command)
        new = CompareEntity(new_command)

        old_set = set(old_command)
        new_set = set(new_command)

        if old_set != new_set:
            old.diff = old_set - new_set
            new.diff = new_set - old_set
            return CompareResult(False, "Commands are different", old, new)

        return CompareResult(True, "", old, new)

    def compare_volumes(self, container: Container) -> CompareResult:
        attrs = container.attrs
        old_volumes = ["{}:{}:{}".format(m["Source"], m["Destination"], m["Mode"]) for m in attrs["Mounts"]]
        new_volumes = ["{}:{}:{}".format(key, value["bind"], value["mode"]) for key, value in self.container_spec.volumes.items()]
        old = CompareEntity(old_volumes)
        new = CompareEntity(new_volumes)
        old_set = set(old_volumes)
        new_set = set(new_volumes)
        if old_set != new_set:
            old.diff = old_set - new_set
            new.diff = new_set - old_set
            return CompareResult(False, "Volumes are different", old, new)
        return CompareResult(True, "", old, new)

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

    def compare_ports(self, container: Container) -> CompareResult:
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

        old = CompareEntity(old_ports)
        new = CompareEntity(new_ports)

        old_set = set(old_ports)
        new_set = set(new_ports)

        if old_set != new_set:
            old.diff = old_set - new_set
            new.diff = new_set - old_set
            return CompareResult(False, "Ports are different", old, new)
        return CompareResult(True, "", old, new)

    def compare(self, container):

        details = {
            "image": self.compare_image(container),
            "hostname": self.compare_hostname(container),
            "environment": self.compare_environment(container),
            "command": self.compare_command(container),
            "volumes": self.compare_volumes(container),
            "ports": self.compare_ports(container),
        }

        same = True
        for d in details.values():
            if not d.same:
                same = False
                break

        return same, details

    def check_for_updates(self):
        config = self.config.nodes[self.name]
        assert config is not None
        try:
            container = self.client.containers.get(self.container_name)

            if self.mode != "native":
                return "external_with_container", None

            if self.disabled:
                return "disabled_with_container", None

            same, details = self.compare(container)

            if same:
                return "up-to-date", details
            else:
                return "outdated", details

        except NotFound:
            if config["mode"] != "native":
                return "external", None
            if self.disabled:
                return "disabled", None
            return "missing", None

    def update(self, check_result):
        status, details = check_result
        if status == "missing":
            print("Creating %s..." % self.container_name)
            self._container = self.create_container()
        elif status == "outdated":
            print("Recreating %s..." % self.container_name)
            container = self.get_container()
            assert container is not None
            container.stop()
            container.remove()
            self._container = self.create_container()
        elif status == "external_with_container" or status == "disabled_with_container":
            print("Removing %s..." % self.container_name)
            container = self.get_container()
            assert container is not None
            container.stop()
            container.remove()
            self._container = None

    def __repr__(self):
        name = self.name
        mode = self.mode
        container = self.container_name
        return f"<Node {name=} {mode=} {container=}>"


class CliError(Exception):
    def __init__(self, exit_code, output):
        super().__init__(f"{exit_code}|{output!r}")
        self.exit_code = exit_code
        self.output = output


class CliBackend:
    def __init__(self, client: DockerClient, container_name, logger, cli):
        self.client = docker.from_env()
        self.container_name = container_name
        self.logger = logger
        self.cli = cli

    def get_container(self):
        return self.client.containers.get(self.container_name)

    def __getitem__(self, item):  # Not implementing __getaddr__ because `eth.sycning` cannot be invoked as a function name
        def f(*args):
            if len(args) > 0:
                cmd = "%s %s" % (item, " ".join(args))
            else:
                cmd = item
            full_cmd = "%s %s" % (self.cli, cmd)
            if "create" in cmd or "restore" in cmd:
                self.client = docker.from_env(timeout=999999999)
            else:
                self.client = docker.from_env(timeout=20)
            exit_code, output = self.get_container().exec_run(full_cmd)
            text: str = output.decode()
            self.logger.debug("[Execute] %s: exit_code=%s, output=%s", full_cmd, exit_code, output)
            if exit_code != 0:
                raise CliError(exit_code, text)
            return text

        return f
