import json
from dataclasses import dataclass
from typing import Dict, Any, cast

from .base import Service, BaseConfig, Context
from launcher.errors import ForbiddenService, ExecutionError
from .proxy import Proxy


@dataclass
class BoltzNodeStatus:
    status: str
    isUp: bool


class BoltzConfig(BaseConfig):
    pass


class Boltz(Service[BoltzConfig]):
    def __init__(self, context: Context, name: str):
        super().__init__(context, name)
        if self.network == "simnet":
            raise ForbiddenService

        if self.network == "mainnet":
            self.config.image = "exchangeunion/boltz:1.2.0"
        else:
            self.config.image = "exchangeunion/boltz:latest"

    def apply(self):
        super().apply()

        self.volumes.extend([
            "{}:/root/.boltz".format(self.data_dir),
            "{}:/root/.lndbtc".format(self.context.get_service("lndbtc").data_dir),
            "{}:/root/.lndltc".format(self.context.get_service("lndltc").data_dir),
        ])

    def to_json(self) -> Dict[str, Any]:
        result = super().to_json()

        data_dir = cast(Proxy, self.context.get_service("proxy")).DATA_DIR

        result["rpc"].update({
            "bitcoin": {
                "type": "gRPC",
                "host": "boltz",
                "port": 9002,
                "tlsCert": "%s/%s/bitcoin/tls.cert" % (data_dir, self.name),
                "macaroon": "%s/%s/bitcoin/admin.macaroon" % (data_dir, self.name),
            },
            "litecoin": {
                "type": "gRPC",
                "host": "boltz",
                "port": 9102,
                "tlsCert": "%s/%s/litecoin/tls.cert" % (data_dir, self.name),
                "macaroon": "%s/%s/litecoin/admin.macaroon" % (data_dir, self.name),
            },
        })
        return result

    def getinfo(self, chain):
        self.exec("wrapper %s getinfo" % chain)
        return json.loads(output)

    def _check_node(self, node):
        try:
            self.getinfo(node)
            return BoltzNodeStatus(status=node + " up", isUp=True)
        except ExecutionError:
            return BoltzNodeStatus(status=node + " down", isUp=False)

    @property
    def status(self) -> str:
        result = super().status
        if result != "Container running":
            return result

        btc_status = self._check_node("btc")
        ltc_status = self._check_node("ltc")

        if btc_status.isUp and ltc_status.isUp:
            return "Ready"
        else:
            return btc_status.status + "; " + ltc_status.status
