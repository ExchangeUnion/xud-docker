from __future__ import annotations

from typing import TYPE_CHECKING

from .abc import Service, ServiceOptions
from ..options import AncientChaindataDirOption, ModeOption, RpcHostOption, \
    RpcPortOption, InfuraProjectIdOption, InfuraProjectSecretOption, \
    CacheOption, DirOption

if TYPE_CHECKING:
    from ..presets import Preset


class GethOptions(ServiceOptions):
    def __init__(self, service: Service):
        super().__init__(service)
        self.dir = DirOption(service)
        self.ancient_chaindata_dir = AncientChaindataDirOption(service)
        self.mode = ModeOption(service)
        self.rpc_host = RpcHostOption(service)
        self.rpc_port = RpcPortOption(service)
        self.infura_project_id = InfuraProjectIdOption(service)
        self.infura_project_secret = InfuraProjectSecretOption(service)
        self.cache = CacheOption(service)


class Geth(Service[GethOptions]):
    def __init__(self, preset: Preset, name: str = "geth", image: str = "exchangeunion/geth"):
        super().__init__(preset, name, image)
        # TODO eth_provider
