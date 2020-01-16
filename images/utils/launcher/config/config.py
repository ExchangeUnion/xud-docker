import logging
import argparse
import toml
import os
from shutil import copyfile


TESTNET = {
    "bitcoind": {
        "dir": "$testnet_dir/data/bitcoind",
        "external": False,
        "rpc_host": "127.0.0.1",
        "rpc_port": 18332,
        "rpc_user": "xu",
        "rpc_password": "xu",
        "zmqpubrawblock": "127.0.0.1:28332",
        "zmqpubrawtx": "127.0.0.1:28333",
    },
    "litecoind": {
        "dir": "$testnet_dir/data/litecoind",
        "external": False,
        "rpc_host": "127.0.0.1",
        "rpc_port": 19332,
        "rpc_user": "xu",
        "rpc_password": "xu",
        "zmqpubrawblock": "127.0.0.1:28332",
        "zmqpubrawtx": "127.0.0.1:28333",
    },
    "geth": {
        "dir": "$testnet_dir/data/geth",
        "ancient_chaindata_dir": "$testnet_dir/data/geth/chaindata",
        "external": False,
        "rpc_host": "127.0.0.1",
        "rpc_port": 8545,
        "infura_project_id": None,
        "infura_project_secret": None,
    }
}

MAINNET = {
    "bitcoind": {
        "dir": "$mainnet_dir/data/bitcoind",
        "external": False,
        "rpc_host": "127.0.0.1",
        "rpc_port": 8332,
        "rpc_user": "xu",
        "rpc_password": "xu",
        "zmqpubrawblock": "127.0.0.1:28332",
        "zmqpubrawtx": "127.0.0.1:28333",
    },
    "litecoind": {
        "dir": "$mainnet_dir/data/litecoind",
        "external": False,
        "rpc_host": "127.0.0.1",
        "rpc_port": 9332,
        "rpc_user": "xu",
        "rpc_password": "xu",
        "zmqpubrawblock": "127.0.0.1:28332",
        "zmqpubrawtx": "127.0.0.1:28333",
    },
    "geth": {
        "dir": "$mainnet_dir/data/geth",
        "ancient_chaindata_dir": "$mainnet_dir/data/geth/chaindata",
        "external": False,
        "rpc_host": "127.0.0.1",
        "rpc_port": 8545,
        "infura_project_id": None,
        "infura_project_secret": None,
    }
}


class ContainerConfig:
    def __init__(self, value, expand):
        self._dict = value
        self._expand = expand

    def __getitem__(self, item):
        if self._dict is None:
            return None
        return self._expand(self._dict.get(item, None))

    def __setitem__(self, key, value):
        if value is None:
            return
        if key in self._dict:
            self._dict[key] = value


class Containers:
    def __init__(self, network, expand):
        if network == "simnet":
            self._config = {}
        elif network == "testnet":
            self._config = TESTNET
        elif network == "mainnet":
            self._config = MAINNET
        self._expand = expand

    def __getitem__(self, item):
        return ContainerConfig(self._config.get(item, None), self._expand)


def merge_bitcoind(container, parsed):
    keys = ["dir", "external", "rpc_host", "rpc_port", "rpc_user", "rpc_password", "zmqpubrawblock", "zmqpubrawtx"]
    for key in keys:
        container[key] = parsed.get(key.replace("_", "-"), None)
    container["rpc_port"] = int(container["rpc_port"])


def merge_litecoind(container, parsed):
    merge_bitcoind(container, parsed)


def merge_geth(container, parsed):
    keys = ["dir", "ancient_chaindata_dir", "external", "rpc_host", "rpc_port", "infura_project_id", "infura_project_secret"]
    for key in keys:
        container[key] = parsed.get(key.replace("_", "-"), None)


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
    def __init__(self):
        self._logger = logging.getLogger("launcher.Config")
        self.branch = "master"
        self.disable_update = False
        self.external_ip = None
        self.home_dir = os.environ["HOME_DIR"]
        self.network = os.environ["NETWORK"]
        self.network_dir = os.environ["NETWORK_DIR"]
        self.containers = Containers(self.network, self._expand)
        self.backup_dir = None

    def parse(self):
        self._parse_config_file()
        self._parse_command_line_arguments()

    def _parse_command_line_arguments(self):
        parser = ArgumentParser(argument_default=argparse.SUPPRESS, prog="launcher")
        parser.add_argument("--branch", "-b")
        parser.add_argument("--disable-update", action="store_true")
        parser.add_argument("--simnet-dir")
        parser.add_argument("--testnet-dir")
        parser.add_argument("--mainnet-dir")
        parser.add_argument("--external-ip")
        parser.add_argument("--backup-dir")

        self._args = parser.parse_args()
        self._logger.debug("Parsed command-line arguments: %r", self._args)

        if hasattr(self._args, "branch"):
            self.branch = self._args.branch

        if hasattr(self._args, "disable_update"):
            self.disable_update = True

        if hasattr(self._args, "external_ip"):
            self.external_ip = self._args.external_ip

        if hasattr(self._args, "backup_dir"):
            self.backup_dir = self._args.backup_dir

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
                    merge_litecoind(self.containers["litecoind"], parsed["litecoind"])

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
