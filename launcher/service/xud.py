import json
import os
from dataclasses import dataclass, field
from typing import Dict, Any, cast

from launcher.errors import ExecutionError
from .base import BaseConfig, Service, Context
from .proxy import Proxy


@dataclass
class XudConfig(BaseConfig):
    preserve_config: bool = field(init=False, metadata={
        "help": "Preserve lnd.conf file during updates"
    })


class Xud(Service[XudConfig]):
    def __init__(self, context: Context, name: str):
        super().__init__(context, name)
        if self.network == "mainnet":
            self.config.image = "exchangeunion/xud:1.2.4"
        else:
            self.config.image = "exchangeunion/xud:latest"

        self.config.preserve_config = False

    def apply(self):
        super().apply()
        self.environment["NODE_ENV"] = "production"
        if self.config.preserve_config:
            self.environment["PRESERVE_CONFIG"] = "true"
        else:
            self.environment["PRESERVE_CONFIG"] = "false"

        self.volumes.extend([
            "{}:/root/.xud".format(self.data_dir),
            "{}:/root/.lndbtc".format(self.context.get_service("lndbtc").data_dir),
            "{}:/root/.lndltc".format(self.context.get_service("lndltc").data_dir),
            "{}:/root/backup".format(self.context.backup_dir),
        ])

        if self.network == "simnet":
            self.ports.append("28885")
        elif self.network == "testnet":
            self.ports.append("18885")
        elif self.network == "mainnet":
            self.ports.append("8885")

    @property
    def rpcport(self) -> int:
        if self.network == "simnet":
            return 28886
        elif self.network == "testnet":
            return 18886
        elif self.network == "mainnet":
            return 8886

    def to_json(self) -> Dict[str, Any]:
        result = super().to_json()

        data_dir = cast(Proxy, self.context.get_service("proxy")).DATA_DIR

        result["rpc"].update({
            "type": "gRPC",
            "host": self.name,
            "port": self.rpcport,
            "tlsCert": "%s/%s/tls.cert" % (data_dir, self.name),
        })
        return result

    def getinfo(self):
        output = self.exec("xucli getinfo -j")
        return json.loads(output)

    @property
    def status(self) -> str:
        result = super().status
        if result != "Container running":
            return result

        try:
            info = self.getinfo()
            lndbtc_status = info["lndMap"][0][1]["status"]
            lndltc_status = info["lndMap"][1][1]["status"]
            connext_status = info["connext"]["status"]

            if "Ready" == lndbtc_status \
                    or "Ready" == lndltc_status \
                    or "Ready" == connext_status:
                return "Ready"

            if "has no active channels" in lndbtc_status \
                    or "has no active channels" in lndltc_status \
                    or "has no active channels" in connext_status:
                return "Waiting for channels"
            else:
                not_ready = []
                if lndbtc_status != "Ready":
                    not_ready.append("lndbtc")
                if lndltc_status != "Ready":
                    not_ready.append("lndltc")
                if connext_status != "Ready":
                    not_ready.append("connext")
                return "Waiting for " + ", ".join(not_ready)

        except ExecutionError as e:
            if "xud is locked" in e.output:
                nodekey = os.path.join(self.data_dir, "nodekey.dat")
                if not os.path.exists(nodekey):
                    return "Wallet missing. Create with xucli create/restore."
                return "Wallet locked. Unlock with xucli unlock."
            elif "tls cert could not be found at /root/.xud/tls.cert" in e.output:
                return "Starting..."
            elif "xud is starting" in e.output:
                return "Starting..."
            elif f"could not connect to xud at localhost:{self.rpcport}, is xud running?" == e.output:
                return "Starting..."
            else:
                raise
