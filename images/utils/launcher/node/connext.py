from .base import Node, CliBackend, CliError
import json
import secrets
import string


class ConnextApiError(Exception):
    pass


class ConnextApi:
    def __init__(self, backend):
        self._backend = backend

    def is_healthy(self):
        try:
            result = self._backend["http://localhost:8000/ping"]()
            return result == ""
        except CliError as e:
            raise ConnextApiError("Starting...")

def generate_admin_token():
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(20))

def get_vector_config(chain_id, channel_factory_address, transfer_registry_address, eth_provider):
    # This is a placeholder mnemonic that is required for startup, but is not being used since it will be overwritten by xud.
    placeholder_mnemonic = "crazy angry east hood fiber awake leg knife entire excite output scheme"
    vector_json = {
        "adminToken": generate_admin_token(),
        "chainAddresses": {
            chain_id: {
                "channelFactoryAddress": channel_factory_address,
                "transferRegistryAddress": transfer_registry_address,
            }
        },
        "chainProviders": {
            chain_id: eth_provider
        },
        "domainName": "",
        "logLevel": "debug",
        "messagingUrl": "https://messaging.connext.network",
        "production": True,
        "mnemonic": placeholder_mnemonic
    }
    if chain_id is not "1337":
        # we only need chainAddresses for simnet where the contract
        # addresses need to be specified manually
        del vector_json['chainAddresses']
    vector_json_string = json.dumps(vector_json)
    vector_config = "VECTOR_CONFIG=%s" % vector_json_string
    return vector_config


class Connext(Node):
    def __init__(self, name, ctx):
        super().__init__(name, ctx)

        eth_provider = ""
        if self.network in ["testnet", "mainnet"]:
            geth = self.config.nodes["geth"]
            if geth["mode"] == "external":
                rpc_host = geth["external_rpc_host"]
                rpc_port = geth["external_rpc_port"]
                eth_provider = f'http://{rpc_host}:{rpc_port}'
            elif geth["mode"] == "infura":
                project_id = geth["infura_project_id"]
                project_secret = geth["infura_project_secret"]
                if self.network == "mainnet":
                    eth_provider = f'https://mainnet.infura.io/v3/{project_id}'
                elif self.network == "testnet":
                    eth_provider = f'https://rinkeby.infura.io/v3/{project_id}'
            elif geth["mode"] == "light":
                eth_provider = geth["eth_provider"]
            elif geth["mode"] == "native":
                eth_provider = 'http://geth:8545'
        else:
            # simnet PoA eth provider
            eth_provider = "http://35.234.110.95:8545"

        channel_factory_address = ""
        transfer_registry_address = ""
        if self.network in ["simnet"]:
            chain_id = "1337"
            # for simnet we also have to specify the contract addresses
            channel_factory_address = "0x2b19530c81E97FBc2feD79E813E4723D9bA7343B"
            transfer_registry_address = "0xD74aafE4e2E723C53c82eb0ba8716eD386389123"
        elif self.network in ["testnet"]:
            chain_id = "4"
        elif self.network in ["mainnet"]:
            chain_id = "1"

        environment = [
            get_vector_config(chain_id, channel_factory_address, transfer_registry_address, eth_provider),
            "VECTOR_SQLITE_FILE=/database/store.db",
            "VECTOR_PROD=true",
        ]

        # legacy connext indra stuff
        if self.network == "mainnet":
            environment = [
                "LEGACY_MODE=true",
                "CONNEXT_NODE_URL=https://connext.boltz.exchange",
            ]
        if self.network in ["mainnet"]:
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
                environment.extend([
                    f'CONNEXT_ETH_PROVIDER_URL=https://mainnet.infura.io/v3/{project_id}'
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
