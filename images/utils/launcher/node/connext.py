from .base import Node, CliBackend, CliError
import json


class ConnextApiError(Exception):
    pass


class ConnextApi:
    def __init__(self, backend):
        self._backend = backend

    def is_healthy(self):
        try:
            result = self._backend["http://localhost:5040/health"]()
            return result == ""
        except CliError as e:
            raise ConnextApiError("connext is staring... try again in a few seconds")


class Connext(Node):
    def __init__(self, name, ctx):
        super().__init__(name, ctx)

        if self.network == "simnet":
            environment = [
                "CONNEXT_ETH_PROVIDER_URL=http://130.211.223.61:8545",
                "CONNEXT_NODE_URL=http://130.211.223.61:8080",
            ]
        else:
            environment = []

        if self.network in ["testnet", "mainnet"]:
            geth = self.config.nodes["geth"]
            if geth["mode"] == "external":
                rpc_host = geth["external_rpc_host"]
                rpc_port = geth["external_rpc_port"]
                environment.extend([
                    f'CONNEXT_ETH_PROVIDER_URL=http://{rpc_host}:{rpc_port}'
                ])
                # TODO: add CONNEXT_NODE_URL
            elif geth["mode"] == "infura":
                project_id = geth["infura_project_id"]
                project_secret = geth["infura_project_secret"]
                if self.network == "mainnet":
                    environment.extend([
                        f'CONNEXT_ETH_PROVIDER_URL=https://mainnet.infura.io/v3/{project_id}'
                    ])
                elif self.network == "testnet":
                    environment.extend([
                        f'CONNEXT_ETH_PROVIDER_URL=https://ropsten.infura.io/v3/{project_id}'
                    ])

        self.container_spec.environment.extend(environment)

        self._cli = "curl -s"
        self.api = ConnextApi(CliBackend(self.client, self.container_name, self._logger, self._cli))

    def status(self):
        status = super().status()
        if status == "exited":
            # TODO: analyze exit reason
            return "Container exited"
        elif status == "running":
            try:
                healthy = self.api.is_healthy()
                if healthy:
                    return "Ready"
                else:
                    return "Starting..."
            except ConnextApiError as e:
                self._logger.exception("Failed to get advanced running status")
                return str(e)
            except:
                self._logger.exception("Failed to get advanced running status")
                return "Container running"
        else:
            return status
