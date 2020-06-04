from __future__ import annotations
from typing import TYPE_CHECKING

from .abc import Preset
from ..services import Bitcoind, Litecoind, Geth, Lndbtc, Lndltc, Connext, Xud, Service

if TYPE_CHECKING:
    from ..config import Config


class MainnetPreset(Preset):
    def __init__(self, config: Config):
        super().__init__(config)
        self.services = [
            Bitcoind(self, image="exchangeunion/bitcoind:0.19.1"),
            Litecoind(self, image="exchangeunion/litecoind:0.17.1"),
            Geth(self, image="exchangeunion/geth:1.9.14"),
            Lndbtc(self, image="exchangeunion/lnd:0.10.0-beta"),
            Lndltc(self, image="exchangeunion/lnd:0.9.0-beta-ltc"),
            Connext(self, image="exchangeunion/connext:latest"),
            Xud(self, image="exchangeunion/xud:1.0.0-beta.3"),
        ]

    @property
    def prefix(self) -> str:
        return "mainnet"