import platform
import socket
from dataclasses import dataclass, field
from typing import List

from .base import BaseConfig, Service, Context
from launcher.errors import NoProcess


@dataclass
class ProxyConfig(BaseConfig):
    tls: bool = field(init=False, metadata={
        "help": "Enabled TLS support"
    }, default=True)


class Proxy(Service[ProxyConfig]):
    tls: bool

    DATA_DIR = "/root/network/data"

    def __init__(self, context: Context, name: str):
        super().__init__(context, name)

        if self.network == "mainnet":
            self.config.image = "exchangeunion/proxy:1.2.0"
        else:
            self.config.image = "exchangeunion/proxy:latest"

        self.data_dir = "/root/.proxy"
        self.tls = False

    def apply(self):
        super().apply()

        if platform.system() == "Windows":
            docker_sock = "//var/run/docker.sock"
        else:
            docker_sock = "/var/run/docker.sock"

        self.volumes.extend([
            "{}:/root/.proxy".format(self.data_dir),
            "{}:/var/run/docker.sock".format(docker_sock),
            "{}:/root/network".format(self.context.network_dir),
        ])

        self.tls = self.config.tls

        if self.config.tls:
            self.command.append("--tls")

        self.ports.append("127.0.0.1:%s:8080" % self.apiport)

    @property
    def apiport(self) -> int:
        if self.network == "simnet":
            return 28889
        elif self.network == "testnet":
            return 18889
        elif self.network == "mainnet":
            return 8889

    @property
    def apiurl(self) -> str:
        if self.tls:
            return "https://localhost:%s" % self.apiport
        return "http://localhost:%s" % self.apiport

    def _test_apiport(self) -> bool:
        s = socket.socket()
        try:
            s.connect(("127.0.0.1", self.apiport))
            return True
        except:
            return False
        finally:
            s.close()

    def _find_process(self) -> int:
        try:
            output = self.exec("pgrep proxy")
            return int(output)
        except Exception as e:
            raise NoProcess from e

    def _grep_error_logs(self) -> List[str]:
        lines = self.logs()
        result = []
        for line in lines:
            line = line.lower()
            if "error" in line or "panic" in line:
                result.append(line)
        return result

    @property
    def status(self) -> str:
        result = super().status
        if result != "Container running":
            return result

        if self._test_apiport():
            return "Ready"

        try:
            self._find_process()
        except NoProcess:
            return "Error: no process"

        errors = self._grep_error_logs()
        if len(errors) > 0:
            return "Error: has error logs"

        return "Starting..."
