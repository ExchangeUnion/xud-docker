from docker import DockerClient
from .base import Node, InvalidNetwork, CliBackend, CliError
from ..config import Config
import json
import socket

class BitcoindApiError(Exception):
    pass

class BitcoindApi:
    def __init__(self, backend):
        self._backend = backend

    def getblockchaininfo(self):
        try:
            return json.loads(self._backend["getblockchaininfo"]())
        except CliError as e:
            # error code: -28
            # error message:
            # Loading block index...
            lines = e.output.splitlines()
            if len(lines) == 3 and "error message:" in lines[1]:
                raise BitcoindApiError(lines[2].strip())
            else:
                raise BitcoindApiError(e.output)


class Bitcoind(Node):
    def __init__(self, client: DockerClient, config: Config, name, litecoin: bool = False):
        self.litecoin = litecoin
        super().__init__(client, config, name)
        self.external = config.containers[name]["external"]
        if self.external:
            c = config.containers[name]
            self.external_config = {
                "rpc_host": c["rpc_host"],
                "rpc_port": c["rpc_port"],
                "rpc_user": c["rpc_user"],
                "rpc_password": c["rpc_password"],
                "zmqpubrawblock": c["zmqpubrawblock"],
                "zmqpubrawtx": c["zmqpubrawtx"],
            }

        command = [
            "-server",
            "-rpcuser=xu",
            "-rpcpassword=xu",
            "-disablewallet",
            "-txindex",
            "-zmqpubrawblock=tcp://0.0.0.0:28332",
            "-zmqpubrawtx=tcp://0.0.0.0:28333",
            "-logips",
            "-rpcallowip=::/0",
            "-rpcbind=0.0.0.0",
        ]
        if self.network == "testnet":
            command.append("-rpcport=18332")
            command.append("-testnet")
        elif self.network == "mainnet":
            command.append("-rpcport=8332")
        else:
            raise InvalidNetwork(self.network)

        if self.litecoin:
            command = []

        data_dir = config.containers[name]["dir"]
        if self.litecoin:
            volumes = {
                data_dir: {
                    'bind': '/root/.litecoin',
                    'mode': 'rw'
                }
            }
        else:
            volumes = {
                data_dir: {
                    'bind': '/root/.bitcoin',
                    'mode': 'rw'
                }
            }

        self.container_spec.command.extend(command)
        self.container_spec.volumes.update(volumes)

        if self.litecoin:
            self._cli = "litecoin-cli -rpcuser=xu -rpcpassword=xu"
        else:
            self._cli = "bitcoin-cli -rpcuser=xu -rpcpassword=xu"
        if self.network == "testnet":
            self._cli += " -testnet"

        self.api = BitcoindApi(CliBackend(client, self.container_name, self._logger, self._cli))

    @property
    def image(self):
        if self.litecoin:
            return "exchangeunion/litecoind:0.17.1"
        else:
            return "exchangeunion/bitcoind:0.19.0.1"

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
                info = self.api.getblockchaininfo()
                current: int = info["blocks"]
                total: int = info["headers"]
                if current > 0 and current == total:
                    return "Ready"
                else:
                    if total == 0:
                        return "Syncing 0.00% (0/0)"
                    else:
                        p = current / total * 100
                        if p > 0.005:
                            p = p - 0.005
                        else:
                            p = 0
                        return "Syncing %.2f%% (%d/%d)" % (p, current, total)
            except BitcoindApiError as e:
                return str(e)
            except:
                self._logger.exception("Failed to get advanced running status")
                return "Container running"
        else:
            return status

    def cli(self, cmd, shell):
        if self.external:
            return
        return super().cli(cmd, shell)


class Litecoind(Bitcoind):
    def __init__(self, *args):
        super().__init__(*args, litecoin=True)
