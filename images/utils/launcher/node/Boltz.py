import json
from dataclasses import dataclass

from .Node import Node, NodeApi, CliError


@dataclass
class BoltzNodeStatus:
    status: str
    isUp: bool


class BoltzApiError(Exception):
    pass


class BoltzApi(NodeApi):
    def getinfo(self, node):
        try:
            info = self.cli(node + " getinfo")
            return json.loads(info)
        except CliError as e:
            raise BoltzApiError(e.output)


class Boltz(Node[BoltzApi]):
    @property
    def cli_prefix(self):
        return "wrapper"

    def check_node(self, node):
        try:
            self.api.getinfo(node)
            return BoltzNodeStatus(status=node + " up", isUp=True)
        except:
            return BoltzNodeStatus(status=node + " down", isUp=False)

    def application_status(self):
        btc_status = self.check_node("btc")
        ltc_status = self.check_node("ltc")

        if btc_status.isUp and ltc_status.isUp:
            return "Ready"
        else:
            return btc_status.status + "; " + ltc_status.status
