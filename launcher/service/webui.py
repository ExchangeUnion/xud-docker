from .base import BaseConfig, Service, Context


class WebuiConfig(BaseConfig):
    pass


class Webui(Service[WebuiConfig]):
    def __init__(self, context: Context, name: str):
        super().__init__(context, name)
        if self.network == "mainnet":
            self.config.image = "exchangeunion/webui:1.0.0"
        else:
            self.config.image = "exchangeunion/webui:latest"

        self.config.disabled = True

    def apply(self):
        super().apply()


