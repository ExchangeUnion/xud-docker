import json
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime, timedelta
from urllib.request import urlopen, Request

import demjson

from .Node import Node, NodeApi


class GethApi(NodeApi):
    def eth_syncing(self):
        js_obj = self.cli("--exec eth.syncing attach")
        return demjson.decode(js_obj)

    def eth_blockNumber(self):
        js_obj = self.cli("--exec eth.blockNumber attach")
        return demjson.decode(js_obj)


class Geth(Node[GethApi]):
    def __init__(self, name, ctx):
        super().__init__(name, ctx)

        if self.mode == "external":
            self.external_config = {
                "rpc_host": self.node_config["external_rpc_host"],
                "rpc_port": self.node_config["external_rpc_port"],
            }

        if self.mode == "infura":
            self.infura_config = {
                "project_id": self.node_config["infura_project_id"],
                "project_secret": self.node_config["infura_project_secret"],
            }

        if self.mode == "light":
            providers = self.config.eth_providers
            eth_provider = self.get_fastest_provider(providers)
            if not eth_provider:
                raise RuntimeError("No valid ethereum provider")
            self.node_config["eth_provider"] = eth_provider
            self.light_config = {
                "eth_provider": eth_provider
            }

        self.container_spec.environment.extend(self.get_environment())

        self.container_spec.command.extend([
            "--cache {}".format(self.node_config["cache"])
        ])

    @property
    def cli_prefix(self):
        if self.network == "testnet":
            return "geth --rinkeby"
        elif self.network == "mainnet":
            return "geth"

    def get_environment(self):
        result = []
        if self.use_custom_ancient_chaindata():
            result.append("CUSTOM_ANCIENT_CHAINDATA=true")
        else:
            result.append("CUSTOM_ANCIENT_CHAINDATA=false")
        return result

    def use_custom_ancient_chaindata(self):
        for v in self.node_config["volumes"]:
            if v["container"] == "/root/.ethereum-ancient-chaindata":
                return True
        return False

    def check_eth_rpc(self, url):
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
            self.logger.info("The ethereum RPC %s net version is %s", url, result)
            return True
        except:
            return False

    def get_fastest_provider(self, providers):
        timeout = 30
        min_delay = timedelta(seconds=timeout)
        provider = None
        with ThreadPoolExecutor(max_workers=len(providers)) as executor:
            fs = {executor.submit(self.get_provider_delay, p): p for p in providers}
            done, not_done = wait(fs, timeout)
            for f in done:
                p = fs[f]
                try:
                    delay = f.result()
                    if delay < min_delay:
                        min_delay = delay
                        provider = p
                except:
                    pass
        return provider

    def get_provider_delay(self, provider):
        try:
            t1 = datetime.now()
            ok = self.check_eth_rpc(provider)
            t2 = datetime.now()
            if ok:
                return t2 - t1
        except:
            self.logger.exception("Failed to get provider %s delay", provider)
        return None

    def get_external_status(self):
        rpc_host = self.external_config["rpc_host"]
        rpc_port = self.external_config["rpc_port"]
        url = f"http://{rpc_host}:{rpc_port}"
        if self.check_eth_rpc(url):
            return "Ready (connected to external)"
        else:
            return "Unavailable (connection to external failed)"

    def get_infura_status(self):
        project_id = self.infura_config["project_id"]
        if self.network == "mainnet":
            url = f"https://mainnet.infura.io/v3/{project_id}"
        elif self.network == "testnet":
            url = f"https://rinkeby.infura.io/v3/{project_id}"
        else:
            raise RuntimeError(f"{self.network} won't use Infura")
        if self.check_eth_rpc(url):
            return "Ready (connected to Infura)"
        else:
            return "Unavailable (connection to Infura failed)"

    def get_light_status(self):
        eth_provider = self.light_config["eth_provider"]
        if self.check_eth_rpc(eth_provider):
            return "Ready (light mode)"
        else:
            return "Unavailable (light mode failed)"

    def status(self):
        if self.mode == "external":
            return self.get_external_status()
        elif self.mode == "infura":
            return self.get_infura_status()
        elif self.mode == "light":
            return self.get_light_status()
        else:
            return super().status()

    def application_status(self):
        try:
            syncing = self.api.eth_syncing()
            if syncing:
                current: int = syncing["currentBlock"]
                total: int = syncing["highestBlock"]
                p = current / total * 100
                if p > 0.005:
                    p = p - 0.005
                else:
                    p = 0
                return "Syncing %.2f%% (%d/%d)" % (p, current, total)
            else:
                block_number = self.api.eth_blockNumber()
                if block_number == 0:
                    return "Waiting for sync"
                else:
                    return "Ready"
        except:
            self.logger.exception("Failed to get advanced running status")
            return "Waiting for geth to come up..."
