from .base import Node, CliBackend, CliError
import json
import re
from datetime import datetime, timedelta


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
            return json.loads(self._backend["getinfo"]())
        except CliError as e:
            raise LndApiError(e.output)


class Lnd(Node):
    def __init__(self, name, ctx, chain: str):
        super().__init__(name, ctx)
        self.chain = chain

        command = self.get_command()
        environment = self.get_environment()

        self.container_spec.command.extend(command)
        self.container_spec.environment.extend(environment)

        self._cli = f"lncli -n {self.network} -c {self.chain}"
        self.api = LndApi(CliBackend(self.client, self.container_name, self._logger, self._cli))

    @property
    def p2p_port(self) -> int:
        if self.chain == "bitcoin":
            if self.network == "mainnet":
                return 9735
            elif self.network == "testnet":
                return 19735
            elif self.network == "simnet":
                return 29735
        elif self.chain == "litecoin":
            if self.network == "mainnet":
                return 10735
            elif self.network == "testnet":
                return 20735
            elif self.network == "simnet":
                return 30735

    def get_command(self):
        network = self.network
        chain = self.chain
        p2p_port = self.p2p_port

        opts = [
            f"--listen=0.0.0.0:{p2p_port}",
            f"--rpclisten=0.0.0.0:10009",
            f"--restlisten=0.0.0.0:8080",
            f"--protocol.wumbo-channels",
            f"--{chain}.active",
            f"--{chain}.{network}",
        ]

        externalip = self.config.external_ip
        if externalip:
            opts += [
                f"--externalip={externalip}:{p2p_port}",
            ]

        # configure chain specific options (shared between networks)
        if chain == "bitcoin":
            opts += [
                "--max-cltv-expiry=5000",
            ]
        elif chain == "litecoin":
            opts += [
                "--max-cltv-expiry=20000",
            ]

        # configure network specific options (shared between modes)
        if network == "simnet":
            opts += [
                f"--trickledelay=1",
                f"--debuglevel=debug",
                f"--nobootstrap",
                f"--minbackoff=30s",
                f"--maxbackoff=24h",
                f"--chan-enable-timeout=0m10s",
                f"--routing.assumechanvalid",
                f"--{chain}.node=neutrino",
                f"--{chain}.defaultchanconfs=6",
            ]
            if chain == "bitcoin":
                opts += [
                    "--neutrino.connect=btcd.simnet.exchangeunion.com:38555",
                ]
            elif chain == "litecoin":
                opts += [
                    "--neutrino.connect=btcd.simnet.exchangeunion.com:39555",
                ]
        elif network == "testnet":
            opts += [
                f"--trickledelay=15000",
                #f"--autopilot.active=false",
                f"--debuglevel=ATPL=debug"
            ]
        elif network == "mainnet":
            opts += [
                f"--trickledelay=15000",
                #f"--autopilot.active=false",
                f"--debuglevel=ATPL=debug"
            ]

        # configure backend node for testnet and mainnet
        if network != "simnet":
            if chain == "bitcoin":
                backend = "bitcoind"
                backend_config = self.config.nodes[backend]
            else:
                backend = "litecoind"
                backend_config = self.config.nodes[backend]

            mode = backend_config["mode"]

            if mode == "native":
                # use bitcoind/litecoind backend
                if chain == "bitcoin":
                    block_port = 28332
                    tx_port = 28333
                else:
                    block_port = 29332
                    tx_port = 29333

                opts += [
                    f"--{chain}.node={backend}"
                    f"--{backend}.rpchost={backend}",
                    f"--{backend}.rpcuser=xu",
                    f"--{backend}.rpcpass=xu",
                    f"--{backend}.zmqpubrawblock=tcp://{backend}:{block_port}",
                    f"--{backend}.zmqpubrawtx=tcp://{backend}:{tx_port}",
                ]
            elif mode == "external":
                # use bitcoind/litecoind backend
                rpchost = backend_config["external_rpc_host"]
                rpcuser = backend_config["external_rpc_user"]
                rpcpass = backend_config["external_rpc_password"]
                zmqpubrawblock = backend_config["external_zmqpubrawblock"]
                zmqpubrawtx = backend_config["external_zmqpubrawtx"]

                opts += [
                    f"--{chain}.node={backend}"
                    f"--{backend}.rpchost={rpchost}",
                    f"--{backend}.rpcuser={rpcuser}",
                    f"--{backend}.rpcpass={rpcpass}",
                    f"--{backend}.zmqpubrawblock={zmqpubrawblock}",
                    f"--{backend}.zmqpubrawtx={zmqpubrawtx}",
                ]
            elif mode == "neutrino" or mode == "light":
                # use Neutrino backend
                opts += [
                    f"--{chain}.node=neutrino",
                    f"--routing.assumechanvalid",
                ]
                # add Neutrino peers
                if network == "testnet":
                    if chain == "bitcoin":
                        opts += [
                            "--neutrino.addpeer=bitcoin.michael1011.at:18333",
                            "--neutrino.addpeer=btc.kilrau.com:18333",
                        ]
                    elif chain == "litecoin":
                        opts += [
                            "--neutrino.connect=ltcd.michael1011.at:19335",
                            "--neutrino.connect=ltc.kilrau.com:19335",
                        ]
                elif network == "mainnet":
                    if chain == "bitcoin":
                        opts += [
                            "--neutrino.addpeer=bitcoin.michael1011.at:8333",
                            "--neutrino.addpeer=btc.kilrau.com:8333",
                            "--neutrino.addpeer=thun.droidtech.it:8333",
                        ]
                    elif chain == "litecoin":
                        opts += [
                            "--neutrino.connect=ltcd.michael1011.at:9333",
                            "--neutrino.connect=ltc.kilrau.com:9333",
                        ]

        return opts

    def get_environment(self):
        environment = [
            f"CHAIN={self.chain}",
            f"P2P_PORT={self.p2p_port}",
        ]
        return environment

    def get_current_height(self):
        try:
            c = self.get_container()
            since = datetime.now() - timedelta(hours=1)
            lines = c.logs(since=since).decode().splitlines()
            p = re.compile(r".*New block: height=(\d+),.*")
            for line in reversed(lines):
                m = p.match(line)
                if m:
                    return int(m.group(1))
            return None
        except:
            return None

    def status(self):
        status = super().status()
        if status == "exited":
            # TODO analyze exit reason
            return "Container exited"
        elif status == "running":
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
        else:
            return status


class Lndbtc(Lnd):
    def __init__(self, *args):
        super().__init__(*args, chain="bitcoin")


class Lndltc(Lnd):
    def __init__(self, *args):
        super().__init__(*args, chain="litecoin")
