import json
import logging
import re
from datetime import datetime, timedelta
from threading import Event

from launcher.utils import get_percentage
from .base import Node, CliBackend, CliError

logger = logging.getLogger(__name__)


class InvalidChain(Exception):
    def __init__(self, chain: str):
        super().__init__("Invalid chain: %s", chain)


class LndApiError(Exception):
    pass


class LndApi:
    def __init__(self, backend):
        self._backend = backend

    def getinfo(self):
        try:
            info = self._backend.invoke("getinfo")
            return json.loads(info)
        except CliError as e:
            raise LndApiError(e.output)


class CFHeaderState:
    def __init__(self):
        self.current = 0
        self.total = 0
        self.ready = False

    def __repr__(self):
        return "%s/%s (%s)" % (self.current, self.total, self.ready)

    @property
    def message(self):
        return "Syncing " + get_percentage(self.current, self.total)


class Lnd(Node):
    def __init__(self, name, ctx, chain: str):
        super().__init__(name, ctx)
        self.chain = chain

        command = self.get_command()
        environment = self.get_environment()

        self.container_spec.command.extend(command)
        self.container_spec.environment.extend(environment)

        self._cli = f"lncli -n {self.network} -c {self.chain}"
        self.api = LndApi(CliBackend(self.name, self.container_name, self._cli))

    def get_command(self):
        if self.network != "simnet":
            return []
        if self.chain == "bitcoin":
            # TODO better to have --alias
            # nohup lnd-btc --noseedbackup --rpclisten=127.0.0.1:10002 --listen=127.0.0.1:10012 --restlisten=8002 --datadir=./data --logdir=./logs  --nobootstrap --no-macaroons --bitcoin.active --bitcoin.simnet  --btcd.rpcuser=xu --btcd.rpcpass=xu --debuglevel=debug --alias="BTC@$xname" --btcd.rpchost=127.0.0.1:18556  --btcd.rpccert=$cert --bitcoin.node neutrino  --neutrino.connect btcd.simnet.exchangeunion.com:38555 --chan-enable-timeout=0m10s --max-cltv-expiry=5000 > /dev/null 2>&1 &
            return [
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
                "--max-cltv-expiry=5000"
            ]
        if self.chain == "litecoin":
            # nohup lnd-ltc --noseedbackup --rpclisten=127.0.0.1:10001 --listen=127.0.0.1:10011 --restlisten=8001 --datadir=./data --logdir=./logs --nobootstrap --no-macaroons --litecoin.active --litecoin.simnet --debuglevel=debug --alias="LTC@$xname" --litecoin.node neutrino --neutrino.connect btcd.simnet.exchangeunion.com:39555 --chan-enable-timeout=0m10s --max-cltv-expiry=20000 > /dev/null 2>&1 &
            return [
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
                "--max-cltv-expiry=20000"
            ]

    def get_environment(self):
        environment = [f"CHAIN={self.chain}"]

        external_ip = self.config.external_ip
        if external_ip is not None:
            environment.append(f"EXTERNAL_IP={external_ip}")

        if self.network in ["testnet", "mainnet"]:
            if self.name == "lndbtc":
                layer1_node = self.config.nodes["bitcoind"]
            else:
                layer1_node = self.config.nodes["litecoind"]

            if layer1_node["mode"] == "neutrino" or layer1_node["mode"] == "light":
                environment.extend([
                    f'NEUTRINO=True',
                ])
            elif layer1_node["mode"] == "external":
                environment.extend([
                    f'RPCHOST={layer1_node["external_rpc_host"]}',
                    f'RPCUSER={layer1_node["external_rpc_user"]}',
                    f'RPCPASS={layer1_node["external_rpc_password"]}',
                    f'ZMQPUBRAWBLOCK={layer1_node["external_zmqpubrawblock"]}',
                    f'ZMQPUBRAWTX={layer1_node["external_zmqpubrawtx"]}',
                ])
        return environment

    def get_current_height(self):
        try:
            c = self.get_container()
            since = datetime.now() - timedelta(hours=1)
            # TODO use base logs
            lines = c.logs(since=since).decode().splitlines()
            p = re.compile(r".*New block: height=(\d+),.*")
            for line in reversed(lines):
                m = p.match(line)
                if m:
                    return int(m.group(1))
            return None
        except:
            return None

    def get_external_status(self) -> str:
        # TODO check external status
        return "Ready (connected to external)"

    def status(self):
        if self.mode == "external":
            return self.get_external_status()

        status = super().status()
        if status != "Container running":
            return status
        try:
            info = self.api.getinfo()
            synced_to_chain = info["synced_to_chain"]
            total = info["block_height"]
            current = self.get_current_height()
            if current:
                if total <= current:
                    msg = "Ready"
                else:
                    msg = "Syncing"
                    p = current / total * 100
                    if p > 0.005:
                        p = p - 0.005
                    else:
                        p = 0
                    msg += " %.2f%% (%d/%d)" % (p, current, total)
            else:
                if synced_to_chain:
                    msg = "Ready"
                else:
                    msg = "Syncing"
            return msg
        except LndApiError as e:
            # [lncli] Wallet is encrypted. Please unlock using 'lncli unlock', or set password using 'lncli create' if this is the first time starting lnd.
            if "Wallet is encrypted" in str(e):
                return "Wallet locked. Unlock with xucli unlock."
        except:
            self._logger.exception("Failed to get advanced running status")
        return "Waiting for lnd ({}) to come up...".format(self.chain)

    def ensure_ready(self, stop: Event):
        # [lncli] open /root/.lnd/tls.cert: no such file or directory
        # [lncli] unable to read macaroon path (check the network setting!): open /root/.lnd/data/chain/bitcoin/testnet/admin.macaroon: no such file or directory
        # [lncli] Wallet is encrypted. Please unlock using 'lncli unlock', or set password using 'lncli create' if this is the first time starting lnd.
        while not stop.is_set():
            exit_code, output = self.exec(self._cli + " getinfo")
            if exit_code == 0:
                break
            if "unable to read macaroon path" in output:
                break
            if "Wallet is encrypted" in output:
                break
            stop.wait(3)

    def update_cfheader(self, state: CFHeaderState, stop: Event):
        container = self.container
        started_at = container.attrs["State"]["StartedAt"]  # e.g. 2020-06-22T17:26:01.541780733Z
        started_at = started_at.split(".")[0]
        t_utc = datetime.strptime(started_at, "%Y-%m-%dT%H:%M:%S")
        t_local = datetime.fromtimestamp(t_utc.timestamp())

        p0 = re.compile(r"^.*Fully caught up with cfheaders at height (\d+), waiting at tip for new blocks$")
        if self.config.network == "simnet":
            p1 = re.compile(r"^.*Writing cfheaders at height=(\d+) to next checkpoint$")
        else:
            p1 = re.compile(r"^.*Fetching set of checkpointed cfheaders filters from height=(\d+).*$")
        p2 = re.compile(r"^.*Syncing to block height (\d+) from peer.*$")

        if stop.is_set():
            return

        for line in container.logs(stream=True, follow=True, since=t_local):
            if stop.is_set():
                break
            line = line.decode().strip()
            m = p0.match(line)

            if m:
                #logger.debug("[%s] (match 1) %s", self.name, line)
                state.current = int(m.group(1))
                state.ready = True
                h = max(state.current, state.total)
                state.current = h
                state.total = h
                break

            m = p1.match(line)
            if m:
                #logger.debug("[%s] (match 2) %s", self.name, line)
                state.current = int(m.group(1))
                continue

            m = p2.match(line)
            if m:
                #logger.debug("[%s] (match 3) %s", self.name, line)
                state.total = int(m.group(1))

        logger.debug("[%s] update_cfheader ends" % self.name)


class Lndbtc(Lnd):
    def __init__(self, *args):
        super().__init__(*args, chain="bitcoin")


class Lndltc(Lnd):
    def __init__(self, *args):
        super().__init__(*args, chain="litecoin")
