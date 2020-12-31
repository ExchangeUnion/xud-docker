import logging
from abc import ABC
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import List, Dict, Generic, TypeVar, get_args, Any, Callable, Optional

from .errors import FatalError
from .utils import run
import os


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
    data_dir: str
    logs_dir: str
    backup_dir: str

    external_ip: Optional[str]

    get_service: Callable[[str], 'Service']

    executor: ThreadPoolExecutor

    def __init__(self, network: str, network_dir: str):
        self.network = network
        self.network_dir = network_dir
        self.data_dir = os.path.join(self.network_dir, "data")
        self.logs_dir = os.path.join(self.network_dir, "logs")
        self.backup_dir = os.path.join(self.network_dir, "backup")
        self.external_ip = None
        self.executor = ThreadPoolExecutor(max_workers=16, thread_name_prefix="Pool")


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
    def status(self) -> str:
        if self.disabled:
            return "Disabled"

        cmd = "docker ps --format {{.State}} -f name=%s" % self.container_name
        output = run(cmd)
        if output == "":
            return "Container missing"
        lines = output.splitlines()
        if len(lines) > 1:
            raise FatalError("multiple results: %s: %s" % (cmd, lines))
        else:
            return "Container " + lines[0]
