import logging
import argparse
import toml
import os
from shutil import copyfile
import json
from urllib.request import urlopen

from ..utils import normalize_path


TESTNET = {
    "bitcoind": {
        "dir": "$testnet_dir/data/bitcoind",
        "neutrino": False,
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
        "neutrino": False,
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
    keys = ["dir", "neutrino", "external", "rpc_host", "rpc_port", "rpc_user", "rpc_password", "zmqpubrawblock", "zmqpubrawtx"]
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


class InvalidHomeDir(Exception):
    def __init__(self, reason):
        super().__init__(reason)


class InvalidNetworkDir(Exception):
    def __init__(self, reason):
        super().__init__(reason)


class NodesJsonMissing(Exception):
    pass


class Config:
    def __init__(self):
        self.logger = logging.getLogger("launcher.Config")
        self.branch = "master"
        self.disable_update = False
        self.external_ip = None
        self.network = os.environ["NETWORK"]
        self.home_dir = self.ensure_home_dir()
        self.network_dir = None
        self.backup_dir = None
        self.restore_dir = None

        self.containers = Containers(self.network, self._expand)
        self.nodes = None

    def parse(self):
        self.parse_command_line_arguments()
        self.network_dir = "{}/{}".format(self.home_dir.replace("/mnt/hostfs", ""), self.network)
        self.parse_config_file()
        self.apply_general_command_line_arguments()
        self.network_dir = self.ensure_network_dir()
        self.parse_network_config_file()
        self.apply_network_command_line_arguments()

    def ensure_home_dir(self):
        home = os.environ["HOST_HOME"]
        home_dir = "/mnt/hostfs" + home + "/.xud-docker"
        if os.path.exists(home_dir):
            if not os.path.isdir(home_dir):
                raise InvalidHomeDir("{} is not a directory".format(home_dir))
            else:
                if not os.access(home_dir, os.R_OK):
                    raise InvalidHomeDir("{} is not readable".format(home_dir))
                if not os.access(home_dir, os.W_OK):
                    raise InvalidHomeDir("{} is not writable".format(home_dir))
        else:
            os.mkdir(home_dir)
        return home_dir

    def ensure_network_dir(self):
        network_dir = "/mnt/hostfs" + normalize_path(self.network_dir)
        if os.path.exists(network_dir):
            if not os.path.isdir(network_dir):
                raise InvalidNetworkDir("{} is not a directory".format(network_dir))
            else:
                if not os.access(network_dir, os.R_OK):
                    raise InvalidNetworkDir("{} is not readable".format(network_dir))
                if not os.access(network_dir, os.W_OK):
                    raise InvalidNetworkDir("{} is not writable".format(network_dir))
        else:
            os.makedirs(network_dir)

        if not os.path.exists(network_dir + "/logs"):
            os.mkdir(network_dir + "/logs")
        return network_dir

    def parse_command_line_arguments(self):
        parser = ArgumentParser(argument_default=argparse.SUPPRESS, prog="launcher")
        parser.add_argument("--branch", "-b")
        parser.add_argument("--disable-update", action="store_true")
        parser.add_argument("--simnet-dir")
        parser.add_argument("--testnet-dir")
        parser.add_argument("--mainnet-dir")
        parser.add_argument("--external-ip")
        parser.add_argument("--backup-dir")
        parser.add_argument("--dev", action="store_true")
        parser.add_argument("--bitcoin-neutrino", type=bool)
        parser.add_argument("--nodes-json")

        self.args = parser.parse_args()
        self.logger.info("[Config] Parsed command-line arguments: %r", self.args)

    def apply_general_command_line_arguments(self):
        if hasattr(self.args, "branch"):
            self.branch = self.args.branch

        if hasattr(self.args, "disable_update"):
            self.disable_update = True

        if hasattr(self.args, "external_ip"):
            self.external_ip = self.args.external_ip

        if hasattr(self.args, f"{self.network}_dir"):
            self.network_dir = getattr(self.args, f"{self.network}_dir")

    def apply_network_command_line_arguments(self):
        if hasattr(self.args, "bitcoin_neutrino"):
            self.containers["bitcoind"]["neutrino"] = self.args.bitcoin_neutrino

    def parse_config_file(self):
        network = self.network
        config_file = f"{self.home_dir}/xud-docker.conf"
        sample_config_file = f"{self.home_dir}/sample-xud-docker.conf"
        try:
            copyfile(os.path.dirname(__file__) + "/xud-docker.conf", sample_config_file)
            with open(config_file) as f:
                parsed = toml.load(f)
                self.logger.info("[Config] Parsed TOML file %s: %r", config_file, parsed)
                key = f"{network}-dir"
                if key in parsed:
                    self.network_dir = parsed[key]
        except FileNotFoundError:
            copyfile(os.path.dirname(__file__) + f"/xud-docker.conf", config_file)

    def parse_network_config_file(self):
        network = self.network
        config_file = f"{self.network_dir}/{network}.conf"
        sample_config_file = f"{self.network_dir}/sample-{network}.conf"
        try:
            copyfile(os.path.dirname(__file__) + f'/{network}.conf', sample_config_file)
            with open(config_file) as f:
                parsed = toml.load(f)
                self.logger.info("[Config] Parsed TOML file %s: %r", config_file, parsed)

                if "backup-dir" in parsed and len(parsed["backup-dir"].strip()) > 0:
                    self.backup_dir = parsed["backup-dir"]

                if "bitcoind" in parsed:
                    merge_bitcoind(self.containers["bitcoind"], parsed["bitcoind"])

                if "litecoind" in parsed:
                    merge_litecoind(self.containers["litecoind"], parsed["litecoind"])

                if "geth" in parsed:
                    merge_geth(self.containers["geth"], parsed["geth"])
        except FileNotFoundError:
            copyfile(os.path.dirname(__file__) + f"/{network}.conf", config_file)

        # Backward compatible with lnd.env
        lndenv = f"{self.home_dir}/{network}/lnd.env"
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

    @property
    def logfile(self):
        if self.network_dir:
            network = self.network
            suffix = os.environ["LOG_TIMESTAMP"]
            return f"{self.network_dir}/logs/{network}-{suffix}.log"
        return None

    def get_nodes(self):
        if not self.nodes:
            try:
                r = urlopen(f"https://raw.githubusercontent.com/ExchangeUnion/xud-docker/{self.branch}/nodes.json")
                self.nodes = json.load(r)[self.network]
            except:
                if hasattr(self.args, "nodes_json"):
                    f = "/mnt/hostfs" + normalize_path(self.args.nodes_json)
                    self.nodes = json.load(open(f))[self.network]
                else:
                    raise NodesJsonMissing()
        return self.nodes
