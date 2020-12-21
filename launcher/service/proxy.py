import socket
from typing import List
import platform

from .base import BaseConfig, Service, Context
from .errors import NoProcess
from .utils import run


class ProxyConfig(BaseConfig):
    pass


class Proxy(Service[ProxyConfig]):
    DATA_DIR = "/root/network/data"

    def __init__(self, context: Context, name: str):
        super().__init__(context, name)
        if self.network == "mainnet":
            self.config.image = "exchangeunion/proxy:1.2.0"
        else:
            self.config.image = "exchangeunion/proxy:latest"

        self.data_dir = "/root/.proxy"

    def apply(self):
        super().apply()

        if platform.system() == "Windows":
            docker_sock = "//var/run/docker.sock"
        else:
            docker_sock = "/var/run/docker.sock"

        self.volumes.extend([
            "{}:/root/.proxy".format(self.data_dir),
            "{}:/var/run/docker.sock".format(docker_sock),
            "{}:/root/network:ro".format(self.context.network_dir),
        ])

        self.ports.append("127.0.0.1:%s:8080" % self.apiport)

    @property
    def apiport(self) -> int:
        if self.network == "simnet":
            return 28889
        elif self.network == "testnet":
            return 18889
        elif self.network == "mainnet":
            return 8889

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
            output = run("docker exec %s pgrep proxy" % self.container_name)
            return int(output)
        except ValueError:
            raise NoProcess

    def _grep_error_logs(self) -> List[str]:
        cmd = "docker logs --since=$(docker inspect --format='{{.State.StartedAt}}' %s) %s " \
              "| { grep -i 'level=error' || true; }" % (self.container_name, self.container_name)
        logs = run(cmd)
        return logs.splitlines()

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
