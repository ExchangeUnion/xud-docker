from .base import Node, CliBackend, CliError


class ArbyApi:
    def __init__(self, backend):
        self._backend = backend

    def is_healthy(self):
        return True


class Arby(Node):
    def __init__(self, name, ctx):
        super().__init__(name, ctx)

        live_cex = self.node_config["live-cex"] \
            if "live-cex" in self.node_config else "false"
        api_key = self.node_config["binance-api-key"] \
            if "binance-api-key" in self.node_config else "123"
        api_secret = self.node_config["binance-api-secret"] \
            if "binance-api-secret" in self.node_config else "abc"
        margin = self.node_config["margin"] \
            if "margin" in self.node_config else "0.04"
        test_centralized_baseasset_balance = self.node_config["test-centralized-baseasset-balance"] \
            if "test-centralized-baseasset-balance" in self.node_config else "123"
        test_centralized_quoteasset_balance = self.node_config["test-centralized-quoteasset-balance"] \
            if "test-centralized-baseasset-balance" in self.node_config else "321"

        if self.network == "simnet":
            rpc_port = "28886"
        elif self.network == "testnet":
            rpc_port = "18886"
        else:
            rpc_port = "8886"

        environment = [
            "NODE_ENV=production",
            "LOG_LEVEL=trace",
            "BASEASSET=ETH",
            "QUOTEASSET=BTC",
            "DATA_DIR=/root/.arby",
            "OPENDEX_CERT_PATH=/root/.xud/tls.cert",
            "OPENDEX_RPC_HOST=xud",
            f"OPENDEX_RPC_PORT={rpc_port}",
            f'BINANCE_API_SECRET={api_secret}',
            f'BINANCE_API_KEY={api_key}',
            f'LIVE_CEX={live_cex}',
            f'MARGIN={margin}',
            f'TEST_CENTRALIZED_EXCHANGE_BASEASSET_BALANCE={test_centralized_baseasset_balance}',
            f'TEST_CENTRALIZED_EXCHANGE_QUOTEASSET_BALANCE={test_centralized_quoteasset_balance}',
        ]

        self.container_spec.environment.extend(environment)

        self._cli = "curl -s"
        self.api = ArbyApi(CliBackend(self.client, self.container_name, self._logger, self._cli))

    def status(self):
        status = super().status()
        status = "Ready"
        return status
