from . import bitcoind
from .base import Context


class Litecoind(bitcoind.Bitcoind):
    def __init__(self, context: Context, name: str):
        super().__init__(context, name)
        if self.network == "mainnet":
            self.config.image = "exchangeunion/litecoind:0.18.1"
        else:
            self.config.image = "exchangeunion/litecoind:latest"

    @property
    def rpcport(self) -> int:
        return 9332 if self.network == "mainnet" else 19332
