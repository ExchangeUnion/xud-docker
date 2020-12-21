from .base import BaseConfig, Service, Context
from launcher.errors import ForbiddenService
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class GethConfig(BaseConfig):
    mode: str = field(init=False, metadata={
        "help": "%(name)s service mode"
    })
    rpchost: str = field(init=False, metadata={
        "help": "External %(name)s RPC hostname"
    })
    rpcport: int = field(init=False, metadata={
        "help": "External %(name)s RPC port"
    })
    infura_project_id: str = field(init=False, metadata={
        "help": "Infura %(name)s provider project ID"
    })
    infura_project_secret: str = field(init=False, metadata={
        "help": "Infura %(name)s provider project secret"
    })
    cache: str = field(init=False, metadata={
        "help": "%(name)s cache size"
    })
    ancient_chaindata_dir: str = field(init=False, metadata={
        "help": "Specify the container's volume mapping ancient chaindata directory. Can be located on a slower HDD."
    })


class Geth(Service[GethConfig]):
    def __init__(self, context: Context, name: str):
        super().__init__(context, name)
        if self.network == "simnet":
            raise ForbiddenService

        if self.network == "mainnet":
            self.config.image = "exchangeunion/geth:1.9.24"
        else:
            self.config.image = "exchangeunion/geth:latest"

        self.config.disabled = True

    def apply(self):
        super().apply()

        self.config.mode = "light"
        self.volumes.append("{}:/root/.ethereum".format(self.data_dir))

    def to_json(self) -> Dict[str, Any]:
        result = super().to_json()
        result["rpc"].update({
            "type": "JSON-RPC",
            "host": "geth",
            "port": 8545,
        })
        return result

