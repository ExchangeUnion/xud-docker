import json
import logging
from concurrent.futures import wait
from datetime import timedelta, datetime
from typing import Dict, Any, cast
from urllib.request import urlopen, Request

from .base import BaseConfig, Service, Context
from launcher.errors import NoInfuraSimnet, ExecutionError
from .geth import Geth

logger = logging.getLogger(__name__)

ETH_PROVIDERS = {
    "testnet": [
        "http://eth.kilrau.com:52041",
        "http://michael1011.at:8546",
        # "http://gethxudxv2k4pv5t5a5lswq2hcv3icmj3uwg7m2n2vuykiyv77legiad.onion:8546"
    ],
    "mainnet": [
        "http://eth.kilrau.com:41007",
        "http://michael1011.at:8545",
        # "http://gethxudxv2k4pv5t5a5lswq2hcv3icmj3uwg7m2n2vuykiyv77legiad.onion:8545"
    ]
}


class ConnextConfig(BaseConfig):
    pass


class Connext(Service[ConnextConfig]):
    def __init__(self, context: Context, name: str):
        super().__init__(context, name)
        if self.network == "mainnet":
            self.config.image = "exchangeunion/connext:1.3.6"
        elif self.network == "simnet":
            self.config.image = "connextproject/vector_node:0.0.34"
        else:
            self.config.image = "exchangeunion/connext:latest"

    def apply(self):
        super().apply()

        self.volumes.append("{}:/app/connext-store".format(self.data_dir))

        if "vector_node" in self.config.image:
            self.environment.update({
                "VECTOR_CONFIG": """{
	"adminToken": "ddrWR8TK8UMTyR",
	"chainAddresses": {
		"1337": {
		"channelFactoryAddress": "0x2eC39861B9Be41c20675a1b727983E3F3151C576",
		"channelMastercopyAddress": "0x7AcAcA3BC812Bcc0185Fa63faF7fE06504D7Fa70",
		"transferRegistryAddress": "0xB2b8A1d98bdD5e7A94B3798A13A94dEFFB1Fe709",
		"TestToken": ""
		}
	},
	"chainProviders": {
		"1337": "http://35.234.110.95:8545"
	},
	"domainName": "",
	"logLevel": "debug",
	"messagingUrl": "https://messaging.connext.network",
	"production": true,
	"mnemonic": "crazy angry east hood fiber awake leg knife entire excite output scheme"
}""",
                "VECTOR_SQLITE_FILE": "/database/store.db",
                "VECTOR_PROD": "true",
            })
        else:
            self.environment["LEGACY_MODE"] = "true"
            if self.network == "simnet":
                self.environment["CONNEXT_ETH_PROVIDER_URL"] = "http://connext.simnet.exchangeunion.com:8545"
                self.environment["CONNEXT_NODE_URL"] = "https://connext.simnet.exchangeunion.com"
            elif self.network == "testnet":
                self.environment["CONNEXT_NODE_URL"] = "https://connext.testnet.exchangeunion.com"
            elif self.network == "mainnet":
                self.environment["CONNEXT_NODE_URL"] = "https://connext.boltz.exchange"

        config = cast(Geth, self.context.get_service("geth")).config

        mode = config.mode
        if mode == "external":
            self.environment["CONNEXT_ETH_PROVIDER_URL"] = f"http://{config.rpchost}:{config.rpcport}"
        elif mode == "infura":
            proj = config.infura_project_id
            if self.network == "mainnet":
                self.environment["CONNEXT_ETH_PROVIDER_URL"] = f"https://mainnet.infura.io/v3/{proj}"
            elif self.network == "testnet":
                self.environment["CONNEXT_ETH_PROVIDER_URL"] = f"https://rinkeby.infura.io/v3/{proj}"
            elif self.network == "simnet":
                raise NoInfuraSimnet
        elif mode == "light":
            self.environment["CONNEXT_ETH_PROVIDER_URL"] = self._select_fastest_provider(self.context)
        elif mode == "native":
            self.environment["CONNEXT_ETH_PROVIDER_URL"] = "http://geth:8545"

    def _check_eth_provider(self, url):
        data = {
            "jsonrpc": "2.0",
            "method": "net_version",
            "params": [],
            "id": 1
        }
        data = json.dumps(data).encode()
        try:
            r = urlopen(Request(url, data=data, headers={
                "Content-Type": "application/json"
            }))
            j = json.loads(r.read().decode())
            result = j["result"]
            # Geth/v1.9.9-omnibus-e320ae4c-20191206/linux-amd64/go1.13.4
            # logger.info("[Ethereum Provider] %s net version: %s", url, result)
            return True
        except:
            return False

    def _select_fastest_provider(self, context: Context):
        providers = ETH_PROVIDERS[self.network]
        timeout = 30
        min_delay = timedelta(seconds=timeout)
        provider = None

        fs = {context.executor.submit(self._get_provider_delay, p): p for p in providers}
        done, not_done = wait(fs, timeout)
        for f in done:
            p = fs[f]
            try:
                delay = f.result()
                logger.debug("[Ethereum Provider] %s latency: %sms", p, int(delay.total_seconds() * 1000))
                if delay < min_delay:
                    min_delay = delay
                    provider = p
            except:
                pass
        return provider

    def _get_provider_delay(self, provider):
        try:
            t1 = datetime.now()
            ok = self._check_eth_provider(provider)
            t2 = datetime.now()
            if ok:
                return t2 - t1
        except:
            logger.exception("Failed to get provider %s delay", provider)
        return None

    def to_json(self) -> Dict[str, Any]:
        result = super().to_json()
        result["rpc"].update({
            "type": "HTTP",
            "host": "connext",
            "port": 5040,
        })
        return result

    @property
    def healthy(self) -> bool:
        try:
            output = self.exec("curl -s http://localhost:5040/health")
            return output == ""
        except ExecutionError as e:
            if e.exit_code == 7:  # (curl) failed to connect to host
                return False
            raise

    @property
    def status(self) -> str:
        result = super().status
        if result != "Container running":
            return result

        if self.healthy:
            return "Ready"

        return "Starting..."
