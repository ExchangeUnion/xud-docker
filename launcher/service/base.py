import logging
import os
import re
from abc import ABC
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import List, Dict, Generic, TypeVar, get_args, Any, Callable, Optional, Generator, Union
import docker
from docker.models.containers import Container
import docker.errors
from datetime import datetime

from launcher.errors import ContainerNotFound, ExecutionError
from launcher.utils import parse_datetime, run


@dataclass
class BaseConfig:
    image: str = field(init=False, metadata={
        "help": "Specify the image of service"
    })
    dir: str = field(init=False, metadata={
        "help": "Specify the data directory of service"
    })
    export_ports: List[str] = field(init=False, metadata={
        "help": "Expose service ports to your host machine"
    })
    disabled: bool = field(init=False, metadata={
        "help": "Enable/Disable service"
    })


T = TypeVar("T", bound=BaseConfig)


class Context:
    network: str
    network_dir: str
    docker_compose_file: str
    config_file: str
    data_dir: str
    logs_dir: str
    default_backup_dir: str
    backup_dir: str
    default_password_file: str
    default_password: bool

    external_ip: Optional[str]

    get_service: Callable[[str], 'Service']

    executor: ThreadPoolExecutor

    def __init__(self, network: str, network_dir: str):
        self.network = network
        self.network_dir = network_dir
        self.docker_compose_file = os.path.join(self.network_dir, "docker-compose.yml")
        self.config_file = os.path.join(self.network_dir, "config.json")
        self.data_dir = os.path.join(self.network_dir, "data")
        self.logs_dir = os.path.join(self.network_dir, "logs")
        self.default_backup_dir = os.path.join(self.network_dir, "backup")
        self.backup_dir = self._load_backup_dir()
        self.default_password_file = os.path.join(self.network_dir, ".default-password")

        self.external_ip = None
        self.executor = ThreadPoolExecutor(max_workers=16, thread_name_prefix="Pool")

    def _load_backup_dir(self) -> str:
        p = re.compile(r"^.*- (.*):/root/backup$")
        with open(self.docker_compose_file) as f:
            for line in f.readlines():
                m = p.match(line)
                if m:
                    return m.group(1)
        return self.default_backup_dir

    @property
    def default_password(self) -> bool:
        return os.path.exists(self.default_password_file)


class Service(ABC, Generic[T]):
    name: str
    context: Context

    hostname: str
    image: str
    command: List[str]
    environment: Dict[str, str]
    ports: List[str]
    volumes: List[str]
    disabled: bool

    config: T

    logger: logging.Logger

    data_dir: str

    docker: docker.DockerClient

    def __init__(self, context: Context, name: str):
        self.context = context
        self.name = name

        self.config = self._init_config()
        self.hostname = name
        self.image = ""
        self.command = []
        self.environment = {}
        self.ports = []
        self.volumes = []
        self.disabled = False

        self.logger = logging.getLogger("launcher.service." + name)

        self.docker = docker.from_env()

    @property
    def network(self) -> str:
        return self.context.network

    def _init_config(self) -> T:
        cfg: BaseConfig = get_args(self.__class__.__orig_bases__[0])[0]()
        cfg.dir = os.path.join(self.context.data_dir, self.name)
        cfg.export_ports = []
        cfg.disabled = False
        return cfg

    def apply(self):
        self.image = self.config.image
        self.ports = self.config.export_ports
        self.disabled = self.config.disabled
        self.environment["NETWORK"] = self.network
        self.data_dir = self.config.dir

    def to_json(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "disabled": self.disabled,
            "rpc": {}
        }

    @property
    def container_name(self):
        return "%s_%s_1" % (self.network, self.name)

    @property
    def _container(self) -> Container:
        try:
            return self.docker.containers.get(self.container_name)
        except docker.errors.NotFound:
            raise ContainerNotFound(self.container_name)

    @property
    def container_status(self) -> str:
        return self._container.status

    @property
    def started_at(self) -> datetime:
        t = self._container.attrs["State"]["StartedAt"]
        t = parse_datetime(t)
        # convert to local timezone datetime
        return t.astimezone()

    @property
    def status(self) -> str:
        if self.disabled:
            return "Disabled"
        return "Container " + self.container_status

    def logs(self, follow=False) -> Union[Generator[str, None, None], List[str]]:
        if follow:
            return self._container.logs(since=int(self.started_at.timestamp()), follow=True, stream=True)
        else:
            lines = self._container.logs(since=int(self.started_at.timestamp()), follow=False, stream=False)
            lines = lines.decode().splitlines()
            return lines

    def exec(self, cmd: str) -> str:
        exit_code, output = self._container.exec_run(cmd)
        output = output.decode().rstrip()
        if exit_code == 0:
            return output
        msg = "[%s] Command '%s' returned non-zero exit status %d." % (self.container_name, cmd, exit_code)
        raise ExecutionError(msg, exit_code, output)

    def start(self):
        self._container.start()

    def stop(self):
        self._container.stop()

    def restart(self):
        self._container.restart()

    def create(self):
        cwd = os.getcwd()
        try:
            os.chdir(self.context.network_dir)
            run("docker-compose up -d --no-start" + self.name)
        finally:
            os.chdir(cwd)

    def remove(self):
        self._container.stop()
        self._container.remove()

    def up(self):
        try:
            _ = self._container
        except ContainerNotFound:
            self.create()
        self.start()
