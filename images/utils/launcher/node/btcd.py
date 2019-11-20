from docker import DockerClient
from .base import Node, CliBackend
from .bitcoind import BitcoindApi
from ..config import Config


class Btcd(Node):
    def __init__(self, client: DockerClient, config: Config, name, litecoin: bool = False):
        self.litecoin = litecoin
        super().__init__(client, config, name)

        if self.litecoin:
            volumes = {
                f"{self.network_dir}/data/ltcd": {
                    'bind': '/root/.ltcd',
                    'mode': 'rw'
                }
            }
        else:
            volumes = {
                f"{self.network_dir}/data/btcd": {
                    'bind': '/root/.btcd',
                    'mode': 'rw'
                }
            }

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
        self.container_spec.volumes.update(volumes)

        if self.litecoin:
            self._cli = "ltcctl --rpcuser=xu --rpcpass=xu"
        else:
            self._cli = "btcctl --rpcuser=xu --rpcpass=xu"
        if self.network == "simnet":
            self._cli += " --simnet"

        self.api = BitcoindApi(CliBackend(client, self.container_name, self._logger, self._cli))

    @property
    def image(self):
        if self.litecoin:
            if self.network == "simnet":
                return "exchangeunion/ltcd-simnet:latest"
            else:
                return "exchangeunion/ltcd:latest"
        else:
            if self.network == "simnet":
                return "exchangeunion/btcd-simnet:latest"
            else:
                return "exchangeunion/btcd:latest"

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
