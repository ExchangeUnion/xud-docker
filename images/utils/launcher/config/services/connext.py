from __future__ import annotations
from typing import TYPE_CHECKING, cast
from .abc import Service, ServiceOptions, NodeApi
if TYPE_CHECKING:
    from .geth import Geth
    from ..presets import Preset


class ConnextApi(NodeApi):
    def is_healthy(self):
        result = self.node.cli("http://localhost:5040/health")
        return result == ""


class ConnextOptions(ServiceOptions):
    pass


class Connext(Service[ConnextOptions, ConnextApi]):
    def __init__(self, preset: Preset, name: str = "connext", image: str = "exchangeunion/connext"):
        super().__init__(preset, name, image)

    @property
    def command(self) -> [str]:
        return []

    @property
    def environment(self) -> [str]:
        result = []
        if self.prefix == "simnet":
            result = [
                "CONNEXT_ETH_PROVIDER_URL=http://connext.simnet.exchangeunion.com:8545",
                "CONNEXT_NODE_URL=https://connext.simnet.exchangeunion.com/api",
            ]
        elif self.prefix == "testnet":
            result = [
                "CONNEXT_NODE_URL=https://connext.testnet.odex.dev/api",
            ]
        elif self.prefix == "mainnet":
            result = [
                "CONNEXT_NODE_URL=https://connext.odex.dev/api",
            ]

        if self.prefix in ["testnet", "mainnet"]:
            geth = cast(Geth, self.preset.service("geth"))
            if geth.mode == "external":
                rpc_host = geth.rpc_host
                rpc_port = geth.rpc_port
                result.extend([
                    f'CONNEXT_ETH_PROVIDER_URL=http://{rpc_host}:{rpc_port}'
                ])
            elif geth.mode == "infura":
                project_id = geth.infura_project_id
                if self.prefix == "mainnet":
                    result.extend([
                        f'CONNEXT_ETH_PROVIDER_URL=https://mainnet.infura.io/v3/{project_id}'
                    ])
                elif self.prefix == "testnet":
                    result.extend([
                        f'CONNEXT_ETH_PROVIDER_URL=https://rinkeby.infura.io/v3/{project_id}'
                    ])
            elif geth.mode == "light":
                eth_provider = geth.eth_provider
                result.extend([
                    f'CONNEXT_ETH_PROVIDER_URL={eth_provider}'
                ])
            elif geth.mode == "native":
                result.extend([
                    f'CONNEXT_ETH_PROVIDER_URL=http://geth:8545'
                ])

        return result

    @property
    def application_status(self) -> str:
        healthy = self.api.is_healthy()
        if healthy:
            return "Ready"
        else:
            return "Starting..."





