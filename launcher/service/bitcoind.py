from .base import BaseConfig, Service, Context
from launcher.errors import ForbiddenService
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class BitcoindConfig(BaseConfig):
    mode: str = field(init=False, metadata={
        "help": "%(name)s service mode"
    })
    rpchost: str = field(init=False, metadata={
        "help": "External %(name)s RPC hostname"
    })
    rpcport: int = field(init=False, metadata={
        "help": "External %(name)s RPC port"
    })
    rpcuser: str = field(init=False, metadata={
        "help": "External %(name)s RPC username"
    })
    rpcpass: str = field(init=False, metadata={
        "help": "External %(name)s RPC password"
    })
    zmqpubrawblock: str = field(init=False, metadata={
        "help": "External %(name)s ZeroMQ raw blocks publication address"
    })
    zmqpubrawtx: str = field(init=False, metadata={
        "help": "External %(name)s ZeroMQ raw transactions publication address"
    })


class Bitcoind(Service[BitcoindConfig]):
    def __init__(self, context: Context, name: str):
        super().__init__(context, name)

        if self.network == "simnet":
            raise ForbiddenService

        if self.network == "mainnet":
            self.config.image = "exchangeunion/bitcoind:0.20.1"
        else:
            self.config.image = "exchangeunion/bitcoind:latest"

        self.config.disabled = True

        self.config.mode = "light"
        self.config.rpchost = ""
        self.config.rpcport = 0
        self.config.rpcuser = ""
        self.config.rpcpass = ""
        self.config.zmqpubrawblock = ""
        self.config.zmqpubrawtx = ""

    def apply(self):
        super().apply()
        self.config.mode = "light"
        self.volumes.append(f"{self.data_dir}:/root/.{self.__class__.__name__.lower()}")

    @property
    def rpcport(self) -> int:
        return 8332 if self.network == "mainnet" else 18332

    def to_json(self) -> Dict[str, Any]:
        result = super().to_json()
        result["rpc"].update({
            "type": "JSON-RPC",
            "host": self.name,
            "port": self.rpcport,
            "username": "xu",
            "password": "xu",
        })
        return result
