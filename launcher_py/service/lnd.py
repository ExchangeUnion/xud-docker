import json
import re
from dataclasses import dataclass, field
from typing import Dict, Any, cast

from .base import BaseConfig, Service, Context
from .bitcoind import Bitcoind
from .errors import SubprocessError
from .litecoind import Litecoind
from .proxy import Proxy
from .utils import run


@dataclass
class LndConfig(BaseConfig):
    mode: str = field(init=False, metadata={
        "help": "%(name)s service mode"
    })
    preserve_config: bool = field(init=False, metadata={
        "help": "Preserve lnd.conf file during updates"
    })


class InvalidChain(Exception):
    pass


class Lnd(Service[LndConfig]):
    chain: str

    PATTERN_NEUTRINO_SYNCING_BEGIN = \
        re.compile(r"^.*Syncing to block height (\d+) from peer.*$")
    PATTERN_NEUTRINO_SYNCING_END = \
        re.compile(r"^.*Fully caught up with cfheaders at height (\d+), waiting at tip for new blocks.*$")
    PATTERN_NEUTRINO_SYNCING = \
        re.compile(r"^.*Fetching set of checkpointed cfheaders filters from height=(\d+).*$")

    def __init__(self, context: Context, name: str, chain: str):
        super().__init__(context, name)
        self.chain = chain

        if self.chain == "bitcoin":
            if self.network == "mainnet":
                self.config.image = "exchangeunion/lndbtc:0.11.1-beta"
            elif self.network == "simnet":
                self.config.image = "exchangeunion/lndbtc-simnet:latest"
            else:
                self.config.image = "exchangeunion/lndbtc:latest"
        elif self.chain == "litecoin":
            if self.network == "mainnet":
                self.config.image = "exchangeunion/lndltc:0.11.0-beta.rc1"
            elif self.network == "simnet":
                self.config.image = "exchangeunion/lndltc-simnet:latest"
            else:
                self.config.image = "exchangeunion/lndltc:latest"
        else:
            raise InvalidChain(self.chain)

        self.config.preserve_config = False

    def apply(self):
        super().apply()

        self.volumes.append("{}:/root/.lnd".format(self.data_dir))

        self.environment["CHAIN"] = self.chain

        if self.config.preserve_config:
            self.environment["PRESERVE_CONFIG"] = "true"
        else:
            self.environment["PRESERVE_CONFIG"] = "false"

        if self.context.external_ip:
            self.environment["EXTERNAL_IP"] = self.context.external_ip

        if self.chain == "bitcoin":
            config = cast(Bitcoind, self.context.get_service("bitcoind")).config
        else:
            config = cast(Litecoind, self.context.get_service("litecoind")).config

        if self.network in ["testnet", "mainnet"]:
            if config.mode in ["neutrino", "light"]:
                self.environment["NEUTRINO"] = "True"
            elif config.mode == "external":
                self.environment.update({
                    "RPCHOST": config.rpchost,
                    "RPCPORT": str(config.rpcport),
                    "RPCUSER": config.rpcuser,
                    "RPCPASS": config.rpcpass,
                    "ZMQPUBRAWBLOCK": config.zmqpubrawblock,
                    "ZMQPUBRAWTX": config.zmqpubrawtx,
                })

        if self.network == "simnet":
            if self.chain == "bitcoin":
                self.command.extend([
                    "--debuglevel=debug",
                    "--nobootstrap",
                    "--minbackoff=30s",
                    "--maxbackoff=24h",
                    "--bitcoin.active",
                    "--bitcoin.simnet",
                    "--bitcoin.node=neutrino",
                    "--bitcoin.defaultchanconfs=6",
                    "--routing.assumechanvalid",
                    "--neutrino.connect=btcd.simnet.exchangeunion.com:38555",
                    "--chan-enable-timeout=0m10s",
                    "--max-cltv-expiry=5000",
                ])
            else:
                self.command.extend([
                    "--debuglevel=debug",
                    "--nobootstrap",
                    "--minbackoff=30s",
                    "--maxbackoff=24h",
                    "--litecoin.active",
                    "--litecoin.simnet",
                    "--litecoin.node=neutrino",
                    "--litecoin.defaultchanconfs=6",
                    "--routing.assumechanvalid",
                    "--neutrino.connect=btcd.simnet.exchangeunion.com:39555",
                    "--chan-enable-timeout=0m10s",
                    "--max-cltv-expiry=20000",
                ])

    def to_json(self) -> Dict[str, Any]:
        result = super().to_json()

        data_dir = cast(Proxy, self.context.get_service("proxy")).DATA_DIR

        result["rpc"].update({
            "type": "gRPC",
            "host": self.name,
            "port": 10009,
            "tlsCert": "%s/%s/tls.cert" % (data_dir, self.name),
            "macaroon": "%s/%s/data/chain/%s/%s/readonly.macaroon" % (data_dir, self.name, self.chain, self.network),
        })
        return result

    def getinfo(self):
        output = run("docker exec %s lncli -n %s -c %s getinfo" % (self.container_name, self.network, self.chain))
        return json.loads(output)

    def _get_logs(self):
        cmd = "docker logs --since=$(docker inspect --format='{{.State.StartedAt}}' %s) %s" % (
        self.container_name, self.container_name)
        logs = run(cmd)
        return logs.splitlines()

    def get_current_height(self):
        lines = self._get_logs()
        # p = re.compile(r".*New block: height=(\d+),.*")
        p = re.compile(r".*Catching up block hashes to height (\d+),.*")
        for line in reversed(lines):
            m = p.match(line)
            if m:
                return int(m.group(1))
        return None

    def get_neutrino_status(self) -> str:
        p_end = self.PATTERN_NEUTRINO_SYNCING_END
        p_begin = self.PATTERN_NEUTRINO_SYNCING_BEGIN
        p = self.PATTERN_NEUTRINO_SYNCING

        lines = self._get_logs()
        total = None
        current = None
        for line in reversed(lines):
            m = p_end.match(line)
            if m:
                self.logger.debug("[Neutrino] SYNCING END: %s", line)
                total = int(m.group(1))
                current = int(m.group(1))
                break

            if not current:
                m = p.match(line)
                if m:
                    self.logger.debug("[Neutrino] SYNCING: %s", line)
                    current = int(m.group(1))

            if not total:
                m = p_begin.match(line)
                if m:
                    self.logger.debug("[Neutrino] SYNCING BEGIN: %s", line)
                    total = int(m.group(1))

            if total and current:
                break

        if not total:
            total = 0

        if not current:
            current = 0

        return self._get_syncing_text(current, total)

    def _get_syncing_text(self, current, total):
        if total == 0:
            return "Syncing 0.00%% (%d/0)" % current
        if total <= current:
            total = max(total, current)
            msg = "Syncing 100.00%% (%d/%d)" % (total, total)
        else:
            msg = "Syncing"
            p = current / total * 100
            if p > 0.005:
                p = p - 0.005
            else:
                p = 0
            msg += " %.2f%% (%d/%d)" % (p, current, total)
        return msg

    @property
    def status(self) -> str:
        result = super().status
        if result != "Container running":
            return result

        try:
            info = self.getinfo()
            synced_to_chain = info["synced_to_chain"]
            total = info["block_height"]
            current = self.get_current_height()
            if current:
                msg = self._get_syncing_text(current, total)
                if "Syncing 100.00%" in msg:
                    return "Ready"
                return msg
            else:
                if synced_to_chain:
                    msg = "Ready"
                else:
                    msg = "Syncing ? (?/%d)" % total
            return msg
        except SubprocessError as e:
            # [lncli] Wallet is encrypted. Please unlock using 'lncli unlock', or set password using 'lncli create' if this is the first time starting lnd.
            if "Wallet is encrypted" in str(e):
                return "Wallet locked. Unlock with xucli unlock."
            if "admin.macaroon: no such file" in str(e):
                msg = self.get_neutrino_status()
                return msg

        return "Starting..."
