import demjson
from .base import Node, CliBackend
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
    def __init__(self, name, ctx):
        super().__init__(name, ctx)

        if self.mode == "external":
            self.external_config = {
                "rpc_host": self.node_config["external_rpc_host"],
                "rpc_port": self.node_config["external_rpc_port"],
            }

        if self.mode == "infura":
            self.infura_config = {
                "project_id": self.node_config["infura_project_id"],
                "project_secret": self.node_config["infura_project_secret"],
            }

        self.container_spec.environment.extend(self.get_environment())

        if self.network == "testnet":
            self._cli = "geth --testnet"
        elif self.network == "mainnet":
            self._cli = "geth"

        self.api = GethApi(CliBackend(self.client, self.container_name, self._logger, self._cli))

    def get_environment(self):
        result = []
        if self.use_custom_ancient_chaindata():
            result.append("CUSTOM_ANCIENT_CHAINDATA=true")
        else:
            result.append("CUSTOM_ANCIENT_CHAINDATA=false")
        return result

    def use_custom_ancient_chaindata(self):
        for v in self.node_config["volumes"]:
            if v["container"] == "/root/.ethereum-ancient-chaindata":
                return True
        return False

    def get_external_status(self):
        s = socket.socket()
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

    def get_infura_status(self):
        s = socket.socket()
        rpc_host = f"{self.network}.infura.io"
        rpc_port = 443
        try:
            s.connect((rpc_host, rpc_port))
            return "Ready (Connected to Infura)"
        except:
            self._logger.exception(f"Failed to connect to Infura node {rpc_host}:{rpc_port}")
            return "Unavailable (Connection to Infura failed)"
        finally:
            s.close()

    def status(self):
        if self.mode == "external":
            return self.get_external_status()

        if self.mode == "infura":
            return self.get_infura_status()

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
