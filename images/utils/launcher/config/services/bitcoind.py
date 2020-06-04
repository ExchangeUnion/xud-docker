from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .abc import Service, Node, ServiceOptions, NodeApi
from ..options import ModeOption, RpcHostOption, RpcPortOption, RpcUserOption, \
    RpcPasswordOption, ZmqpubrawblockOption, ZmqpubrawtxOption, DirOption
from functools import cached_property
import json

if TYPE_CHECKING:
    from ..presets import Preset


class BitcoindOptions(ServiceOptions):
    def __init__(self, service: Service):
        super().__init__(service)
        self.dir = DirOption(service)
        self.mode = ModeOption(service)
        self.rpc_host = RpcHostOption(service)
        self.rpc_port = RpcPortOption(service)
        self.rpc_user = RpcUserOption(service)
        self.rpc_password = RpcPasswordOption(service)
        self.zmqpubrawblock = ZmqpubrawblockOption(service)
        self.zmqpubrawtx = ZmqpubrawtxOption(service)


class BitcoindApi(NodeApi):
    def get_blockchain_info(self):
        return json.loads(self.node.cli("getblockchaininfo"))


class Bitcoind(Node[BitcoindOptions, BitcoindApi]):
    def __init__(self, preset: Preset, name: str = "bitcoind", image: str = "exchangeunion/bitcoind"):
        super().__init__(preset, name, image)
        assert self.prefix in ["testnet", "mainnet"], f"{self.__class__} should be used in testnet and mainnet only"

    @cached_property
    def cli_command(self) -> Optional[str]:
        if self.prefix == "testnet":
            return "bitcoin-cli -testnet -rpcuser=xu -rpcpassword=xu"
        else:
            return "bitcoin-cli -rpcuser=xu -rpcpassword=xu"

    @cached_property
    def command(self) -> [str]:
        result = [
            "-server",
            "-rpcuser=xu",
            "-rpcpassword=xu",
            "-disablewallet",
            "-txindex",
            "-zmqpubrawblock=tcp://0.0.0.0:28332",
            "-zmqpubrawtx=tcp://0.0.0.0:28333",
            "-logips",
            "-rpcallowip=::/0",
            "-rpcbind=0.0.0.0",
        ]

        if self.prefix == "testnet":
            result.append("-rpcport=18332")
            result.append("-testnet")
        else:

            result.append("-rpcport=8332")
        return result

    @cached_property
    def environment(self) -> [str]:
        return []

    @property
    def application_status(self) -> str:
        info = self.api.get_blockchain_info()
        current = info["blocks"]
        total = info["headers"]
        if current > 0 and current == total:
            return "Ready"
        else:
            if total == 0:
                return "Syncing 0.00% (0/0)"
            else:
                p = current / total * 100
                if p > 0.005:
                    p = p - 0.005
                else:
                    p = 0
                return "Syncing %.2f%% (%d/%d)" % (p, current, total)
