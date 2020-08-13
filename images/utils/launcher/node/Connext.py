from .Node import Node, CliError, NodeApi


class ConnextApiError(Exception):
    pass


class ConnextApi(NodeApi):
    def is_healthy(self):
        try:
            result = self.cli("http://localhost:5040/health")
            return result == ""
        except CliError as e:
            raise ConnextApiError("Starting...")


class Connext(Node[ConnextApi]):
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

    @property
    def cli_prefix(self):
        return "curl -s"

    def get_xud_getinfo_connext_status(self):
        xud = self.node_manager.get_node("xud")
        info = xud.api.getinfo()
        status = info["connext"]["status"]
        if status == "Ready":
            return "Ready"
        elif "ECONNREFUSED" in status:
            return "Can't connect to Connext node"
        else:
            return "Starting..."

    def application_status(self):
        try:
            return self.get_xud_getinfo_connext_status()
        except:
            self.logger.exception("Failed to get connext status from xud getinfo")
        try:
            healthy = self.api.is_healthy()
            if healthy:
                return "Ready"
            else:
                return "Starting..."
        except ConnextApiError as e:
            self.logger.exception("Failed to get advanced running status")
            return str(e)
        except:
            self.logger.exception("Failed to get advanced running status")
            return "Waiting for connext to come up..."
