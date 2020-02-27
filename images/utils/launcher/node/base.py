from docker import DockerClient
from docker.errors import NotFound, ImageNotFound
import logging
from typing import List, Dict
from ..config import Config
import os
import sys
import functools
import datetime
import itertools
import json


class InvalidNetwork(Exception):
    def __init__(self, network):
        super().__init__(network)
        self.network = network


class ContainerSpec:
    def __init__(self, name: str, image: str, hostname: str, environment: List[str], command: List[str], volumes: Dict, ports: Dict):
        self.name = name
        self.image = image
        self.hostname = hostname
        self.environment = environment
        self.command = command
        self.volumes = volumes
        self.ports = ports

    def __repr__(self):
        return f"ContainerSpec<{self.name=} {self.image=} {self.hostname=} {self.environment=} {self.command} {self.volumes} {self.ports}>"


class Node:
    def __init__(self, client: DockerClient, config: Config, name):
        self._client = client
        self._config = config
        self.name = name
        self.api = None

        self.container_spec = ContainerSpec(
            name=self.container_name,
            image=self.image,
            hostname=self.name,
            environment=[f"NETWORK={self.network}"],
            command=[],
            volumes={},
            ports={}
        )
        self._container = None

        # used for updates
        self._image_status = None
        self._container_status = None

        self._logger = logging.getLogger("launcher.node." + self.name)

        self._cli = None

        self.image = self._get_image()

    def _get_image(self):
        with open(os.path.dirname(__file__) + '/nodes.json') as f:
            j = json.load(f)
            return j[self.network][self.name]["image"]

    @property
    def container_name(self):
        return f"{self.network}_{self.name}_1"

    @property
    def network(self):
        return self._config.network

    @property
    def network_name(self):
        return self.network + "_default"

    @property
    def network_dir(self):
        return self._config.network_dir

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
        api = self._client.api
        resp = api.create_container(
            image=spec.image,
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
                #cpu_quota=10000,
            ),
            networking_config=api.create_networking_config({
                self.network_name: api.create_endpoint_config(
                    aliases=[self.name]
                )
            }),
        )
        id = resp['Id']
        container = self._client.containers.get(id)
        self._logger.debug(f"Created container: %s (%s)", self.container_name, id)
        return container

    def get_container(self, create=False):
        try:
            return self._client.containers.get(self.container_name)
        except NotFound:
            if create:
                return self.create_container()
            else:
                return None

    def start(self):
        if self._container is None:
            self._container = self.get_container(create=True)
        assert self._container is not None
        self._container.start()
        self._logger.debug(f"Started container: %s (%s)", self.container_name, self._container.id)

    def stop(self):
        if self._container is not None:
            self._container.stop(timeout=180)
            self._logger.debug(f"Stopped container: %s (%s)", self.container_name, self._container.id)

    def remove(self):
        if self._container is not None:
            self._container.remove()
            self._logger.debug(f"Removed container: %s (%s)", self.container_name, self._container.id)

    def status(self):
        self._container = self.get_container()
        if self._container is None:
            return "Container missing"
        return self._container.status

    def exec(self, cmd):
        if self._container is not None:
            return self._container.exec_run(cmd)

    def cli(self, cmd, shell):
        # TODO external cli
        self._logger.debug("cli: %s", cmd)
        full_cmd = "%s %s" % (self._cli, cmd)
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

    def _compare_image(self, x, y, images_check_result, attr):
        if x != y:
            return x, y
        # Compare sha256
        status, pull_image = images_check_result[x]
        if status in ["missing", "outdated"]:
            return x, "%s(%s, %s)" % (y, status, pull_image)
        container_image_sha256 = attr["Image"]
        local_image_sha256 = self._client.images.get(x).id
        if container_image_sha256 != local_image_sha256:
            return "%s(%s)" % (x, local_image_sha256), "%s(%s, %s)" % (y, status, container_image_sha256)
        return None

    def _compare_hostname(self, x, y):
        if x != y:
            return x, y
        return None

    def _compare_environment(self, x, y):
        if x is None:
            x = []
        if set(x) != set(y):
            return set(x) - set(y), set(y) - set(x)
        return None

    def _compare_command(self, x, y):
        if x is None:
            x = []
        if set(x) != set(y):
            return set(x) - set(y), set(y) - set(x)
        return None

    def _compare_volumes(self, x, y):
        # FIXME better normalize volumes
        x = [p["Source"] + ":" + p["Destination"] + ":" + p["Mode"] for p in x]
        y = [key + ":" + value["bind"] + ":" + value["mode"] for key, value in y.items()]
        if set(x) != set(y):
            return set(x) - set(y), set(y) - set(x)
        return None

    def _compare_ports(self, x, y):
        # FIXME better normalize ports
        x = [key + "-" + ",".join([p["HostIp"] + ":" + p["HostPort"] for p in value]) for key, value in x.items() if value is not None]
        y = [key + "-" + (value if isinstance(value, str) else "0.0.0.0:" + str(value)) for key, value in y.items()]
        if set(x) != set(y):
            return set(x) - set(y), set(y) - set(x)
        return None

    def check_updates(self, images_check_result):
        self._logger.debug("Checking container: %s", self.container_name)
        config = self._config.containers[self.name]
        assert config is not None
        try:
            container = self._client.containers.get(self.container_name)

            # TODO make sure config __getitem__ return None if item not exists
            if config["external"]:
                return "external_with_container", None

            attr = container.attrs
            spec = self.container_spec

            details = {
                "image": self._compare_image(attr["Config"]["Image"], spec.image, images_check_result, attr),
                "hostname": self._compare_hostname(attr["Config"]["Hostname"], spec.hostname),
                "environment": self._compare_environment(attr["Config"]["Env"], spec.environment),
                "command": self._compare_command(attr["Config"]["Cmd"], spec.command),
                "volumes": self._compare_volumes(attr["Mounts"], spec.volumes),
                "ports": self._compare_ports(attr["NetworkSettings"]["Ports"], spec.ports),
            }

            self._logger.debug("Container comparing result: %r\nattr: %r\nspec: %r", details, attr, spec)

            if details["environment"] is not None and len(details["environment"][1]) == 0:
                details["environment"] = None

            same = functools.reduce(lambda x, y: x and details[y] is None, details, True)

            if same:
                return "up-to-date", None
            else:
                return "outdated", details

        except NotFound:
            if config["external"]:
                return "external", None
            return "missing", None

    def update(self, check_result):
        status, details = check_result
        if status == "missing":
            print("Creating %s" % self.container_name)
            self._container = self.create_container()
        elif status == "outdated":
            print("Recreating %s" % self.container_name)
            container = self.get_container()
            assert container is not None
            container.stop()
            container.remove()
            self._container = self.create_container()
        elif status == "external_with_container":
            print("Removing %s" % self.container_name)
            container = self.get_container()
            assert container is not None
            container.stop()
            container.remove()
            self._container = None

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


class CliError(Exception):
    def __init__(self, exit_code, output):
        super().__init__(f"{exit_code}|{output!r}")
        self.exit_code = exit_code
        self.output = output


class CliBackend:
    def __init__(self, client: DockerClient, container_name, logger, cli):
        self._client = client
        self._container_name = container_name
        self._logger = logger
        self._cli = cli

    def get_container(self):
        return self._client.containers.get(self._container_name)

    def __getitem__(self, item):  # Not implementing __getaddr__ because `eth.sycning` cannot be invoked as a function name
        def f(*args):
            if len(args) > 0:
                cmd = "%s %s" % (item, " ".join(args))
            else:
                cmd = item
            full_cmd = "%s %s" % (self._cli, cmd)
            exit_code, output = self.get_container().exec_run(full_cmd)
            text: str = output.decode()
            self._logger.debug("%s (exit_code=%d)\n%s", full_cmd, exit_code, text.rstrip())
            if exit_code != 0:
                raise CliError(exit_code, text)
            return text

        return f
