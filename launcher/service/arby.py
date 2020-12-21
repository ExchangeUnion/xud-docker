from dataclasses import dataclass, field

from .base import BaseConfig, Service, Context


@dataclass
class ArbyConfig(BaseConfig):
    live_cex: bool = field(init=False, metadata={
        "help": "Live CEX (deprecated)"
    })
    test_mode: bool = field(init=False, metadata={
        "help": "Whether to issue real orders on the centralized exchange"
    })
    base_asset: str = field(init=False, metadata={
        "help": "Base asset"
    })
    quote_asset: str = field(init=False, metadata={
        "help": "Quote asset"
    })
    cex_base_asset: str = field(init=False, metadata={
        "help": "Centralized exchange base asset"
    })
    cex_quote_asset: str = field(init=False, metadata={
        "help": "Centralized exchange quote asset"
    })
    test_centralized_baseasset_balance: str = field(init=False, metadata={
        "help": "Test centralized base asset balance"
    })
    test_centralized_quoteasset_balance: str = field(init=False, metadata={
        "help": "Test centralized quote asset balance"
    })
    cex: str = field(init=False, metadata={
        "help": "Centralized Exchange"
    })
    cex_api_key: str = field(init=False, metadata={
        "help": "CEX API key"
    })
    cex_api_secret: str = field(init=False, metadata={
        "help": "CEX API secret"
    })
    margin: str = field(init=False, metadata={
        "help": "Trade margin"
    })


class Arby(Service[ArbyConfig]):

    def __init__(self, context: Context, name: str):
        super().__init__(context, name)

        if self.network == "mainnet":
            self.config.image = "exchangeunion/arby:1.4.0"
        else:
            self.config.image = "exchangeunion/arby:latest"

        self.config.disabled = True

        self.config.live_cex = True
        self.config.test_mode = True
        self.config.base_asset = ""
        self.config.quote_asset = ""
        self.config.cex_base_asset = ""
        self.config.cex_quote_asset = ""
        self.config.test_centralized_baseasset_balance = ""
        self.config.test_centralized_quoteasset_balance = ""
        self.config.cex = "binance"
        self.config.cex_api_key = "123"
        self.config.cex_api_secret = "abc"
        self.config.margin = "0.04"

    def apply(self):
        super().apply()
        self.volumes.append(f"{self.data_dir}:/root/.arby")
