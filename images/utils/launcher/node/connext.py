from .base import Node, CliBackend, CliError


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
            raise ConnextApiError("Starting...")


class Connext(Node):
    def __init__(self, name, ctx):
        super().__init__(name, ctx)

        environment = []

        if self.network == "simnet":
            environment = [
                "LEGACY_MODE=true",
                "CONNEXT_ETH_PROVIDER_URL=http://connext.simnet.exchangeunion.com:8545",
                "CONNEXT_NODE_URL=https://connext.simnet.exchangeunion.com",
            ]
        elif self.network == "testnet":
            environment = [
                "LEGACY_MODE=true",
                "CONNEXT_NODE_URL=https://connext.testnet.odex.dev",
            ]
        elif self.network == "mainnet":
            environment = [
                "LEGACY_MODE=true",
                "CONNEXT_NODE_URL=https://connext.boltz.exchange",
            ]

        if self.network in ["testnet", "mainnet"]:
            geth = self.config.nodes["geth"]
            if geth["mode"] == "external":
                rpc_host = geth["external_rpc_host"]
                rpc_port = geth["external_rpc_port"]
                environment.extend([
                    f'CONNEXT_ETH_PROVIDER_URL=http://{rpc_host}:{rpc_port}'
                ])
            elif geth["mode"] == "infura":
                project_id = geth["infura_project_id"]
                project_secret = geth["infura_project_secret"]
                if self.network == "mainnet":
                    environment.extend([
                        f'CONNEXT_ETH_PROVIDER_URL=https://mainnet.infura.io/v3/{project_id}'
                    ])
                elif self.network == "testnet":
                    environment.extend([
                        f'CONNEXT_ETH_PROVIDER_URL=https://rinkeby.infura.io/v3/{project_id}'
                    ])
            elif geth["mode"] == "light":
                eth_provider = geth["eth_provider"]
                environment.extend([
                    f'CONNEXT_ETH_PROVIDER_URL={eth_provider}'
                ])
            elif geth["mode"] == "native":
                environment.extend([
                    f'CONNEXT_ETH_PROVIDER_URL=http://geth:8545'
                ])

        self.container_spec.environment.extend(environment)

        self._cli = "curl -s"
        self.api = ConnextApi(CliBackend(self.client, self.container_name, self._logger, self._cli))

    def get_xud_getinfo_connext_status(self):
        xud = self.node_manager.nodes["xud"]
        info = xud.api.getinfo()
        status = info["connext"]["status"]
        if status == "Ready":
            return "Ready"
        elif "ECONNREFUSED" in status:
            return "Waiting for connext to come up..."
        else:
            return "Starting..."

    def status(self):
        status = super().status()
        if status == "exited":
            # TODO: analyze exit reason
            return "Container exited"
        elif status == "running":
            try:
                return self.get_xud_getinfo_connext_status()
            except:
                self._logger.exception("Failed to get connext status from xud getinfo")
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
                return "Waiting for connext to come up..."
        else:
            return status
