from docker import DockerClient
from .base import Node, CliBackend, CliError
import json
from ..config import Config


class RaidenApiError(Exception):
    pass


class RaidenApi:
    def __init__(self, backend):
        self._backend = backend

    def get_tokens(self):
        try:
            return json.loads(self._backend["http://localhost:5001/api/v1/tokens"]())
        except CliError as e:
            raise RaidenApiError(f"{e.exit_code}|{e.output!r}")


class Raiden(Node):
    def __init__(self, client: DockerClient, config: Config, name: str):
        super().__init__(client, config, name)

        if self.network == "simnet":
            environment = [
                "KEYSTORE_PATH=/root/.raiden/keystore",
                "RESOLVER_ENDPOINT=http://xud:8887/resolveraiden",
                "ETH_RPC_ENDPOINT=35.231.222.142:8546",
                "NETWORK_ID=4321",
                "DATA_DIR=/root/.raiden",
                "API_ADDRESS=0.0.0.0:5001",
                "ENVIRONMENT_TYPE=development",
                "PASSWORD_FILE=/root/.raiden/password.txt",
                "TOKENNETWORK_REGISTRY_CONTRACT=0xdE8A2bdDF39C364e099D0637Dc1a7e2B8f73A4A5",
                "SECRET_REGISTRY_CONTRACT=0xE51d15dEbe0F037ae787336782e3dA43ba653a8D",
                "SERVICE_REGISTRY_CONTRACT=0x4C3Abe4F53247F03A663b55FF02fD403BaBf176d",
                "ONE_TO_N_CONTRACT=0x7337e831cF5BD75B0045050E6C6549cf914A923D",
                "USER_DEPOSIT_CONTRACT=0x19f8B656fBf17a83a5023eEbd675B1Ae5Bb5dF50",
                "MONITORING_SERVICE_CONTRACT=0x3B26A3d3D0c262359d1807863aE0D0FB6831D081",
                "GAS_PRICE=10000000000",
                "MATRIX_SERVER=https://raidentransport.exchangeunion.com",
                "ROUTING_MODE=private",
            ]
        else:
            environment = []

        if self.network in ["testnet", "mainnet"]:
            geth = config.containers["geth"]
            if geth["external"]:
                infura_project_id = geth["infura_project_id"]
                infura_project_secret = geth["infura_project_secret"]
                rpc_host = geth["rpc_host"]
                rpc_port = geth["rpc_port"]
                if infura_project_id is not None:
                    environment.extend([
                        f'RPC_ENDPOINT=https://{self.network}.infura.io/v3/{infura_project_id}'
                    ])
                else:
                    environment.extend([
                        f'RPC_ENDPOINT=http://{rpc_host}:{rpc_port}'
                    ])

        volumes = {
            f"{self.network_dir}/data/raiden": {
                'bind': '/root/.raiden',
                'mode': 'rw'
            },
        }

        self.container_spec.environment.extend(environment)
        self.container_spec.volumes.update(volumes)

        self._cli = "curl -s"
        self.api = RaidenApi(CliBackend(client, self.container_name, self._logger, self._cli))

    @property
    def image(self):
        if self.network == "simnet":
            return "exchangeunion/raiden-simnet:latest"
        else:
            return "exchangeunion/raiden:latest"

    def status(self):
        status = super().status()
        if status == "exited":
            # TODO analyze exit reason
            return "Container exited"
        elif status == "running":
            try:
                tokens = self.api.get_tokens()
                if tokens:
                    return "Ready"
                else:
                    return "Waiting for sync"
            except RaidenApiError as e:
                if str(e) == "7|''":
                    output = "\n".join(list(self.logs(tail=1)))
                    if output == "Waiting for geth to be ready":
                        return "Waiting for sync"
                    elif "Waiting for the ethereum node to synchronize" in output:
                        # Raiden is running in production mode
                        # Checking if the ethereum node is synchronized
                        # Waiting for the ethereum node to synchronize. [Use ^C to exit]
                        return "Waiting for sync"
                    else:
                        return "Container running"
                self._logger.exception("Failed to get advanced running status")
                return str(e)
            except:
                self._logger.exception("Failed to get advanced running status")
                return "Container running"
        else:
            return status
