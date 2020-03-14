from docker import DockerClient
from .base import Node, CliBackend
from .bitcoind import BitcoindApi
from ..config import Config


class Btcd(Node):
    def __init__(self, client: DockerClient, config: Config, name, litecoin: bool = False):
        self.litecoin = litecoin
        super().__init__(client, config, name)

        command = [
            "--simnet",
            "--txindex",
            "--rpcuser=xu",
            "--rpcpass=xu",
            "--rpclisten=:18556",
            "--nolisten",
            "--addpeer=35.231.222.142:39555",
        ]

        self.container_spec.command.extend(command)

        if self.litecoin:
            self._cli = "ltcctl --rpcuser=xu --rpcpass=xu"
        else:
            self._cli = "btcctl --rpcuser=xu --rpcpass=xu"
        if self.network == "simnet":
            self._cli += " --simnet"

        self.api = BitcoindApi(CliBackend(client, self.container_name, self._logger, self._cli))

    def status(self):
        status = super().status()
        if status == "exited":
            # TODO analyze exit reason
            return "Container exited"
        elif status == "running":
            try:
                info = self.api.getblockchaininfo()
                current: int = info["blocks"]
                total: int = info["headers"]
                if current == total:
                    return "Ready"
                else:
                    return "Syncing %.2f (%d/%d)" % (current / total, current, total)
            except:
                self._logger.exception("Failed to get advanced running status")
                return "Container running"
        else:
            return status


class Ltcd(Btcd):
    def __init__(self, *args):
        super().__init__(*args, litecoin=True)
