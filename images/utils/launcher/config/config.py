import logging
import argparse
import toml
import os
from shutil import copyfile
import re
import sys


class ContainerConfig:
    def __init__(self, network, name):
        self.cpu_quota = None
        self.expose_ports = {}
        self.dir = f"${network}_dir/data/{name}"


class BtcdConfig(ContainerConfig):
    def __init__(self, network, name):
        super().__init__(network, name)


class BitcoindConfig(ContainerConfig):
    def __init__(self, network, name):
        super().__init__(network, name)
        self.external = False
        self.rpc_host = None
        self.rpc_port = None
        self.rpc_user = None
        self.rpc_password = None
        self.zmqpubrawblock = None
        self.zmqpubrawtx = None


class GethConfig(ContainerConfig):
    def __init__(self, network, name):
        super().__init__(network, name)
        self.ancient_chaindata_dir = f"${network}_dir/data/geth/chaindata"
        self.external = False
        self.rpc_host = None
        self.rpc_port = None
        self.infura_project_id = None
        self.infura_project_secret = None


class LndConfig(ContainerConfig):
    def __init__(self, network, name):
        super().__init__(network, name)


class RaidenConfig(ContainerConfig):
    def __init__(self, network, name):
        super().__init__(network, name)


class XudConfig(ContainerConfig):
    def __init__(self, network, name):
        super().__init__(network, name)
        if network == "simnet":
            self.expose_ports.update({
                '28885/tcp': 28885
            })
        elif network == "testnet":
            self.expose_ports.update({
                '18885/tcp': 18885
            })
        elif network == "mainnet":
            self.expose_ports.update({
                '8885/tcp': 8885
            })


networks = {
    "simnet": {
        "ltcd": BtcdConfig("simnet", "ltcd"),
        "lndbtc": LndConfig("simnet", "lndbtc"),
        "lndltc": LndConfig("simnet", "lndltc"),
        "raiden": RaidenConfig("simnet", "raiden"),
        "xud": XudConfig("simnet", "xud"),
    },
    "testnet": {
        "bitcoind": BitcoindConfig("testnet", "bitcoind"),
        "litecoind": BitcoindConfig("testnet", "litecoind"),
        "geth": GethConfig("testnet", "geth"),
        "lndbtc": LndConfig("testnet", "lndbtc"),
        "lndltc": LndConfig("testnet", "lndltc"),
        "raiden": RaidenConfig("testnet", "raiden"),
        "xud": XudConfig("testnet", "xud"),
    },
    "mainnet": {
        "bitcoind": BitcoindConfig("mainnet", "bitcoind"),
        "litecoind": BitcoindConfig("mainnet", "litecoind"),
        "geth": GethConfig("mainnet", "geth"),
        "lndbtc": LndConfig("mainnet", "lndbtc"),
        "lndltc": LndConfig("mainnet", "lndltc"),
        "raiden": RaidenConfig("mainnet", "raiden"),
        "xud": XudConfig("mainnet", "xud"),
    }
}


def merge_bitcoind(container, parsed):
    keys = ["dir", "external", "rpc_host", "rpc_port", "rpc_user", "rpc_password", "zmqpubrawblock", "zmqpubrawtx"]
    for key in keys:
        value = parsed.get(key.replace("_", "-"), None)
        if key == "rpc_port" and value:
            value = int(value)
        setattr(container, key, value)


def merge_geth(container, parsed):
    keys = ["dir", "ancient_chaindata_dir", "external", "rpc_host", "rpc_port", "infura_project_id", "infura_project_secret"]
    for key in keys:
        value = parsed.get(key.replace("_", "-"), None)
        setattr(container, key, value)


class ArgumentError(Exception):
    def __init__(self, message, usage):
        super().__init__(message)
        self.usage = usage


class ArgumentParser(argparse.ArgumentParser):
    """
    https://stackoverflow.com/questions/5943249/python-argparse-and-controlling-overriding-the-exit-status-code
    """

    def error(self, message):
        raise ArgumentError(message, self.format_usage())


class Config:
    def __init__(self, args=None):
        self._logger = logging.getLogger(__name__ + ".Config")

        self.branch = "master"
        self.disable_update = False
        self.external_ip = None
        self.home_dir = os.environ["HOME_DIR"]
        self.network = os.environ["NETWORK"]
        self.network_dir = os.environ["NETWORK_DIR"]
        self.containers = networks[self.network]
        self.backup_dir = None

        self._parse_config_file()
        if not args:
            args = sys.argv[1:]
        else:
            args = args.split()
        self._parse_command_line_arguments(args)

    def _parse_command_line_arguments(self, args):
        parser = ArgumentParser(argument_default=argparse.SUPPRESS, prog="launcher")
        parser.add_argument("--branch", "-b")
        parser.add_argument("--disable-update", action="store_true")
        parser.add_argument("--simnet-dir")
        parser.add_argument("--testnet-dir")
        parser.add_argument("--mainnet-dir")
        parser.add_argument("--external-ip")
        parser.add_argument("--backup-dir")
        parser.add_argument("--dev", action="store_true")
        parser.add_argument("--cpu-quotas")
        parser.add_argument("--expose-ports")

        self._logger.debug("%s", args)
        parsed = parser.parse_args(args)

        if hasattr(parsed, "branch"):
            self.branch = parsed.branch

        if hasattr(parsed, "disable_update"):
            self.disable_update = True

        if hasattr(parsed, "external_ip"):
            self.external_ip = parsed.external_ip

        if hasattr(parsed, "backup_dir"):
            self.backup_dir = parsed.backup_dir

        if hasattr(parsed, "cpu_quotas"):
            value = parsed.cpu_quotas
            p = re.compile(r"^\d+$")
            if p.match(value):
                quota = int(value)
                for c in self.containers.values():
                    c.cpu_quota = quota
            else:
                parts = parsed.split(",")
                for p in parts:
                    kv = p.split("/")
                    name = kv[0]
                    quota = int(kv[1])
                    self.containers[name].cpu_quota = quota

        if hasattr(parsed, "expose_ports"):
            value = parsed.expose_ports
            parts = value.split(",")
            for p in parts:
                kv = p.split("/")
                name = kv[0]
                port = "/".join(kv[1:])
                self.containers[name].expose_ports = port

    def _parse_config_file(self):
        network = self.network
        config_file = f"/root/.xud-docker/{network}/{network}.conf"
        sample_config_file = f"/root/.xud-docker/{network}/sample-{network}.conf"
        try:
            copyfile(os.path.dirname(__file__) + f'/{network}.conf', sample_config_file)
            with open(config_file) as f:
                parsed = toml.load(f)
                self._logger.debug("Parsed %s config file: %r", network, parsed)

                if "bitcoind" in parsed:
                    merge_bitcoind(self.containers["bitcoind"], parsed["bitcoind"])

                if "litecoind" in parsed:
                    merge_bitcoind(self.containers["litecoind"], parsed["litecoind"])

                if "geth" in parsed:
                    merge_geth(self.containers["geth"], parsed["geth"])

        except FileNotFoundError:
            copyfile(os.path.dirname(__file__) + f'/{network}.conf', config_file)
            self._logger.debug(f"Copied sample {network}.conf file")

        # Backward compatible with lnd.env
        lndenv = f"/root/.xud-docker/{network}/lnd.env"
        try:
            with open(lndenv) as f:
                for line in f.readlines():
                    if "EXTERNAL_IP" in line:
                        parts = line.split("=")
                        self.external_ip = parts[1].strip()
        except FileNotFoundError:
            pass

    def _expand(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            if "$home_dir" in value:
                value = value.replace("$home_dir", self.home_dir)
            if f"${self.network}_dir" in value:
                value = value.replace(f"${self.network}_dir", self.network_dir)
        return value
