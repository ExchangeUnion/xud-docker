from .abc import Preset
from ..services import Lndbtc, Lndltc, Connext, Xud
from ... import Config


class SimnetPreset(Preset):
    def __init__(self, config: Config):
        super().__init__(config)
        self.services = [
            Lndbtc(image="exchangeunion/lnd:0.10.0-beta-simnet"),
            Lndltc(image="exchangeunion/lnd:0.9.0-beta-ltc-simnet"),
            Connext(image="exchangeunion/connext:latest"),
            Xud(image="exchangeunion/xud:latest"),
        ]

    @property
    def prefix(self) -> str:
        return "simnet"
