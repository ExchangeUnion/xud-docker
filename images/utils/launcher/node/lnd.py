from .base import Node, CliBackend, CliError
import json


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

    def get_command(self):
        if self.network != "simnet":
            return []
        if self.chain == "bitcoin":
            # TODO better to have --alias
            # nohup lnd-btc --noseedbackup --rpclisten=127.0.0.1:10002 --listen=127.0.0.1:10012 --restlisten=8002 --datadir=./data --logdir=./logs  --nobootstrap --no-macaroons --bitcoin.active --bitcoin.simnet  --btcd.rpcuser=xu --btcd.rpcpass=xu --debuglevel=debug --alias="BTC@$xname" --btcd.rpchost=127.0.0.1:18556  --btcd.rpccert=$cert --bitcoin.node neutrino  --neutrino.connect 35.231.222.142:38555 --chan-enable-timeout=0m10s --max-cltv-expiry=5000 > /dev/null 2>&1 &
            return [
                "--debuglevel=debug",
                "--noseedbackup",
                "--nobootstrap",
                "--minbackoff=30s",
                "--maxbackoff=24h",
                "--bitcoin.active",
                "--bitcoin.simnet",
                "--bitcoin.node=btcd",
                "--bitcoin.defaultchanconfs=1",
                "--btcd.rpchost=btcd.simnet.exchangeunion.com:18556"
                "--btcd.rpcuser=xuadmin",
                "--btcd.rpcpass=kilian",
                "--btcd.rpccert=/rpc.cert",
                "--chan-enable-timeout=0m10s",
                "--max-cltv-expiry=5000",
            ]
        if self.chain == "litecoin":
            # nohup lnd-ltc --noseedbackup --rpclisten=127.0.0.1:10001 --listen=127.0.0.1:10011 --restlisten=8001 --datadir=./data --logdir=./logs --nobootstrap --no-macaroons --litecoin.active --litecoin.simnet --debuglevel=debug --alias="LTC@$xname" --litecoin.node neutrino --neutrino.connect 35.231.222.142:39555 --chan-enable-timeout=0m10s --max-cltv-expiry=20000 > /dev/null 2>&1 &
            return [
                "--debuglevel=debug",
                "--noseedbackup",
                "--nobootstrap",
                "--minbackoff=30s",
                "--maxbackoff=24h",
                "--litecoin.active",
                "--litecoin.simnet",
                "--litecoin.node=neutrino",
                "--litecoin.defaultchanconfs=1",
                "--neutrino.connect=35.231.222.142:39555",
                "--chan-enable-timeout=0m10s",
                "--max-cltv-expiry=20000",
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

            if layer1_node["mode"] == "neutrino":
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

    def status(self):
        status = super().status()
        if status == "exited":
            # TODO analyze exit reason
            return "Container exited"
        elif status == "running":
            try:
                info = self.api.getinfo()
                synced_to_chain = info["synced_to_chain"]
                if synced_to_chain:
                    return "Ready"
                else:
                    return "Waiting for sync"
            except LndApiError as e:
                # [lncli] Wallet is encrypted. Please unlock using 'lncli unlock', or set password using 'lncli create' if this is the first time starting lnd.
                if "Wallet is encrypted" in str(e):
                    return "Wallet locked. Unlock with xucli unlock."
            except:
                self._logger.exception("Failed to get advanced running status")
            return "Container running"
        else:
            return status


class Lndbtc(Lnd):
    def __init__(self, *args):
        super().__init__(*args, chain="bitcoin")


class Lndltc(Lnd):
    def __init__(self, *args):
        super().__init__(*args, chain="litecoin")
