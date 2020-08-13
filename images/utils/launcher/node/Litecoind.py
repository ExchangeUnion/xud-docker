from .Bitcoind import Bitcoind


class Litecoind(Bitcoind):
    def cli_command(self) -> str:
        return "litecoind-cli"

    def get_command(self):
        return []
