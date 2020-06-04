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

    @property
    def command(self) -> [str]:
        pass

    @property
    def environment(self) -> [str]:
        pass

    @property
    def application_status(self) -> str:
        pass

    @property
    def mode(self) -> str:
        return self.options.mode.value

    @property
    def rpc_port(self) -> int:
        return self.options.rpc_port.value

    @property
    def rpc_host(self) -> str:
        return self.options.rpc_host.value

    @property
    def infura_project_id(self) -> str:
        return self.options.infura_project_id.value
