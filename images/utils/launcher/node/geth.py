from docker import DockerClient
import demjson
from .base import Node, CliBackend
from ..config import Config
import socket


class GethApi:
    def __init__(self, backend):
        self._backend = backend

    def eth_syncing(self):
        js_obj = self._backend["--exec eth.syncing attach"]()
        return demjson.decode(js_obj)

    def eth_blockNumber(self):
        js_obj = self._backend["--exec eth.blockNumber attach"]()
        return demjson.decode(js_obj)


class Geth(Node):
    def __init__(self, client: DockerClient, config: Config, name):
        super().__init__(client, config, name)
        self.external = config.containers[name]["external"]
        if self.external:
            c = config.containers[name]
            self.external_config = {
                "rpc_host": c["rpc_host"],
                "rpc_port": c["rpc_port"],
                "infura_project_id": c["infura_project_id"],
                "infura_project_secret": c["infura_project_secret"],
            }

        data_dir = config.containers[name]["dir"]
        ancient_chaindata_dir = config.containers[name]["ancient_chaindata_dir"]
        volumes = {
            data_dir: {
                'bind': '/root/.ethereum',
                'mode': 'rw'
            },
            ancient_chaindata_dir: {
                'bind': '/root/.ethereum/chaindata',
                'mode': 'rw'
            },
        }

        self.container_spec.volumes.update(volumes)

        if self.network == "testnet":
            self._cli = "geth --testnet"
        elif self.network == "mainnet":
            self._cli = "geth"

        self.api = GethApi(CliBackend(client, self.container_name, self._logger, self._cli))

    @property
    def image(self):
        return "exchangeunion/geth:1.9.11"

    def start(self):
        if self.external:
            return
        super().start()

    def stop(self):
        if self.external:
            return
        super().stop()

    def remove(self):
        if self.external:
            return
        super().remove()

    def get_external_status(self):
        s = socket.socket()
        infura_project_id = self.external_config["infura_project_id"]
        if infura_project_id:
            rpc_host = f"{self.network}.infura.io"
            rpc_port = 443
        else:
            rpc_host = self.external_config["rpc_host"]
            rpc_port = self.external_config["rpc_port"]
        try:
            s.connect((rpc_host, rpc_port))
            return "Ready (Connected to external)"
        except:
            self._logger.exception(f"Failed to connect to external node {rpc_host}:{rpc_port}")
            return "Unavailable (Connection to external failed)"
        finally:
            s.close()

    def status(self):
        if self.external:
            return self.get_external_status()
        status = super().status()
        if status == "exited":
            # TODO analyze exit reason
            return "Container exited"
        elif status == "running":
            try:
                syncing = self.api.eth_syncing()
                if syncing:
                    current: int = syncing["currentBlock"]
                    total: int = syncing["highestBlock"]
                    p = current / total * 100
                    if p > 0.005:
                        p = p - 0.005
                    else:
                        p = 0
                    return "Syncing %.2f%% (%d/%d)" % (p, current, total)
                else:
                    block_number = self.api.eth_blockNumber()
                    if block_number == 0:
                        return "Waiting for sync"
                    else:
                        return "Ready"
            except:
                self._logger.exception("Failed to get advanced running status")
                return "Container running"
        else:
            return status

    def cli(self, cmd, shell):
        if self.external:
            return
        return super().cli(cmd, shell)
