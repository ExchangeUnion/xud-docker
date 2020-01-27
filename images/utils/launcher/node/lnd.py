from docker import DockerClient
from .base import Node, CliBackend, CliError
import json
from ..config import Config


class InvalidChain(Exception):
    def __init__(self, chain: str):
        super().__init__("Invalid chain: %s", chain)


class LndApiError(Exception):
    pass


class LndApi:
    def __init__(self, backend):
        self._backend = backend

    def getinfo(self):
        try:
            return json.loads(self._backend["getinfo"]())
        except CliError as e:
            raise LndApiError(e.output)


class Lnd(Node):
    def __init__(self, client: DockerClient, config: Config, name: str, chain: str):
        super().__init__(client, config, name)
        self.chain = chain

        external_ip = config.external_ip

        environment = [f"CHAIN={self.chain}"]

        if external_ip is not None:
            environment.append(f"EXTERNAL_IP={external_ip}")

        if self.network in ["testnet", "mainnet"]:
            if name == "lndbtc":
                layer1_node = config.containers["bitcoind"]
            else:
                layer1_node = config.containers["litecoind"]

            if layer1_node.external:
                environment.extend([
                    f'RPCHOST={layer1_node.rpc_host}',
                    f'RPCUSER={layer1_node.rpc_user}',
                    f'RPCPASS={layer1_node.rpc_password}',
                    f'ZMQPUBRAWBLOCK={layer1_node.zmqpubrawblock}',
                    f'ZMQPUBRAWTX={layer1_node.zmqpubrawtx}',
                ])

        volumes = {
            f"{self.network_dir}/data/{name}": {
                'bind': '/root/.lnd',
                'mode': 'rw'
            }
        }
        if self.network == "simnet" and chain == "litecoin":
            volumes[f"{self.network_dir}/data/ltcd"] = {
                'bind': '/root/.ltcd',
                'mode': 'rw'
            }

        self.container_spec.environment.extend(environment)
        self.container_spec.volumes.update(volumes)

        self._cli = f"lncli -n {self.network} -c {self.chain}"
        self.api = LndApi(CliBackend(client, self.container_name, self._logger, self._cli))

    @property
    def image(self):
        if self.network == "simnet":
            return "exchangeunion/lnd-simnet:latest"
        else:
            return "exchangeunion/lnd:0.8.2-beta"

    def status(self):
        status = super().status()
        if status == "exited":
            # TODO analyze exit reason
            return "Container exited"
        elif status == "running":
            try:
                info = self.api.getinfo()
                synced_to_chain = info["synced_to_chain"]
                if synced_to_chain:
                    return "Ready"
                else:
                    return "Waiting for sync"
            except LndApiError as e:
                # [lncli] Wallet is encrypted. Please unlock using 'lncli unlock', or set password using 'lncli create' if this is the first time starting lnd.
                if "Wallet is encrypted" in str(e):
                    return "Wallet locked. Unlock with xucli unlock."
            except:
                self._logger.exception("Failed to get advanced running status")
            return "Container running"
        else:
            return status


class Lndbtc(Lnd):
    def __init__(self, *args):
        super().__init__(*args, chain="bitcoin")


class Lndltc(Lnd):
    def __init__(self, *args):
        super().__init__(*args, chain="litecoin")
