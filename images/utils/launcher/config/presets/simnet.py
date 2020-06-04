from .abc import Preset
from ..services import Lndbtc, Lndltc, Connext, Xud
from ... import Config


class SimnetPreset(Preset):
    def __init__(self, config: Config):
        super().__init__(config)
        self.services = [
            Lndbtc(self, image="exchangeunion/lnd:0.10.0-beta-simnet"),
            Lndltc(self, image="exchangeunion/lnd:0.9.0-beta-ltc-simnet"),
            Connext(self, image="exchangeunion/connext:latest"),
            Xud(self, image="exchangeunion/xud:latest"),
        ]

    @property
    def prefix(self) -> str:
        return "simnet"
