import json
from dataclasses import dataclass
from .base import Node, CliBackend, CliError

@dataclass
class BoltzNodeStatus:
    status: str
    isUp: bool


class BoltzApiError(Exception):
    pass


class BoltzApi:
    def __init__(self, backend):
        self._backend = backend

    def getinfo(self, node):
        try:
            info = self._backend[node + " getinfo"]()
            return json.loads(info)
        except CliError as e:
            raise BoltzApiError(e.output)


class Boltz(Node):
    def __init__(self, name, ctx):
        super().__init__(name, ctx)

        environment = []

        environment.append(f"BOLTZ_OPTS={self.options}")
        self.container_spec.environment.extend(environment)

        self._cli = "wrapper"
        self.api = BoltzApi(CliBackend(self.client, self.container_name, self._logger, self._cli))

    def check_node(self, node):
        try:
            self.api.getinfo(node)
            return BoltzNodeStatus(status=node + " up", isUp=True)
        except:
            return BoltzNodeStatus(status=node + " down", isUp=False)

    def status(self):
        status = super().status()

        if status == "exited":
            return "Container exited"
        elif status == "running":
            btc_status = self.check_node("btc")
            ltc_status = self.check_node("ltc")

            if btc_status.isUp and ltc_status.isUp:
                return "Ready"
            else:
                return btc_status.status + "; " + ltc_status.status

        else:
            return status
