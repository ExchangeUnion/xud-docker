from __future__ import annotations

from typing import TYPE_CHECKING

from .abc import Service, ServiceOptions
from ..options import ModeOption, RpcHostOption, RpcPortOption, RpcUserOption, \
    RpcPasswordOption, ZmqpubrawblockOption, ZmqpubrawtxOption, DirOption

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


class Bitcoind(Service[BitcoindOptions]):
    def __init__(self, preset: Preset, name: str = "bitcoind", image: str = "exchangeunion/bitcoind"):
        super().__init__(preset, name, image)
