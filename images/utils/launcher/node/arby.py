from .base import Node, CliBackend, CliError


class ArbyApi:
    def __init__(self, backend):
        self._backend = backend

    def is_healthy(self):
        return True


class Arby(Node):
    def __init__(self, name, ctx):
        super().__init__(name, ctx)

        api_key = self.node_config["binance-api-key"] \
            if "binance-api-key" in self.node_config else ""
        api_secret = self.node_config["binance-api-secret"] \
            if "binance-api-secret" in self.node_config else ""
        margin = self.node_config["margin"] \
            if "margin" in self.node_config else ""
        environment = [
            "LOG_LEVEL=debug",
            "DATA_DIR=/root/.arby",
            "OPENDEX_CERT_PATH=/root/.xud/tls.cert",
            "OPENDEX_RPC_HOST=xud",
            "OPENDEX_RPC_PORT=28886",
            f'BINANCE_API_SECRET={api_secret}',
            f'BINANCE_API_KEY={api_key}',
            f'MARGIN={margin}',
        ]

        self.container_spec.environment.extend(environment)

        self._cli = "curl -s"
        self.api = ArbyApi(CliBackend(self.client, self.container_name, self._logger, self._cli))

    def status(self):
        status = super().status()
        status = "Hello, Arby."
        return status
