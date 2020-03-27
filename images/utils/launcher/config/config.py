import argparse
import json
import logging
import os
from shutil import copyfile
from urllib.request import urlopen
import re

import toml

from ..utils import normalize_path, get_hostfs_file
from ..errors import NetworkConfigFileValueError, CommandLineArgumentValueError


class PortPublish:
    def __init__(self, value):
        p1 = re.compile(r"^(\d+)$")  # 8080
        p2 = re.compile(r"^(\d+):(\d+)$")  # 80:8080
        p3 = re.compile(r"^(\d+):(\d+):(\d+)$")  # 127.0.0.1:80:8080

        protocol = "tcp"
        if "/" in value:
            parts = value.split("/")
            p = parts[0]
            protocol = parts[1]
            if protocol not in ["tcp", "udp", "sctp"]:
                raise NetworkConfigFileValueError("Invalid protocol: {} ({})".format(protocol, p))

        host = None
        host_port = None
        port = None

        m = p1.match(value)
        if m:
            port = int(m.group(1))
            host_port = port
        else:
            m = p2.match(value)
            if m:
                host_port = int(m.group(1))
                port = int(m.group(2))
            else:
                m = p3.match(value)
                if m:
                    host = m.group(1)
                    host_port = int(m.group(2))
                    port = int(m.group(3))

        self.protocol = protocol
        self.host = host
        self.host_port = host_port
        self.port = port

    def __eq__(self, other):
        if not isinstance(other, PortPublish):
            return False
        if self.host != other.host:
            return False
        if self.host_port != other.host_port:
            return False
        if self.port != other.port:
            return False
        if self.protocol != other.protocol:
            return False
        return True


networks = {
    "simnet": {
        "ltcd": {
            "image": "exchangeunion/ltcd",
            "volumes": [
                {
                    "host": "$data_dir/ltcd",
                    "container": "/root/.ltcd",
                },
            ],
            "ports": [],
            "mode": "native",
        },
        "lndbtc": {
            "image": "exchangeunion/lnd",
            "volumes": [
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lnd",
                },
            ],
            "ports": [],
            "mode": "native",
        },
        "lndltc": {
            "image": "exchangeunion/lnd",
            "volumes": [
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lnd",
                },
                {
                    "host": "$data_dir/ltcd",
                    "container": "/root/.ltcd",
                }
            ],
            "ports": [],
            "mode": "native",
        },
        "raiden": {
            "image": "exchangeunion/raiden",
            "volumes": [
                {
                    "host": "$data_dir/raiden",
                    "container": "/root/.raiden",
                },
            ],
            "ports": [],
            "mode": "native",
        },
        "xud": {
            "image": "exchangeunion/xud",
            "volumes": [
                {
                    "host": "$data_dir/xud",
                    "container": "/root/.xud",
                },
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lndbtc",
                },
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lndltc",
                },
                {
                    "host": "$data_dir/raiden",
                    "container": "/root/.raiden",
                },
                {
                    "host": "/",
                    "container": "/mnt/hostfs",
                },
            ],
            "ports": [PortPublish("28885")],
            "mode": "native",
        }
    },
    "testnet": {
        "bitcoind": {
            "image": "exchangeunion/bitcoind",
            "volumes": [
                {
                    "host": "$data_dir/bitcoind",
                    "container": "/root/.bitcoin",
                }
            ],
            "ports": [],
            "mode": "native",  # external, neutrino
            "external_rpc_host": "127.0.0.1",
            "external_rpc_port": 18332,
            "external_rpc_user": "xu",
            "external_rpc_password": "xu",
            "external_zmqpubrawblock": "127.0.0.1:28332",
            "external_zmqpubrawtx": "127.0.0.1:28333",
        },
        "litecoind": {
            "image": "exchangeunion/litecoind",
            "volumes": [
                {
                    "host": "$data_dir/litecoind",
                    "container": "/root/.litecoin",
                }
            ],
            "ports": [],
            "mode": "native",  # external, neutrino
            "external_rpc_host": "127.0.0.1",
            "external_rpc_port": 19332,
            "external_rpc_user": "xu",
            "external_rpc_password": "xu",
            "external_zmqpubrawblock": "127.0.0.1:29332",
            "external_zmqpubrawtx": "127.0.0.1:29333",
        },
        "geth": {
            "image": "exchangeunion/geth",
            "volumes": [
                {
                    "host": "$data_dir/geth",
                    "container": "/root/.ethereum",
                }
            ],
            "ports": [],
            "mode": "native",  # external, infura
            "external_rpc_host": "127.0.0.1",
            "external_rpc_port": 8545,
            "infura_project_id": None,
            "infura_project_secret": None,
        },
        "lndbtc": {
            "image": "exchangeunion/lnd",
            "volumes": [
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lnd",
                },
            ],
            "ports": [],
            "mode": "native",
        },
        "lndltc": {
            "image": "exchangeunion/lnd",
            "volumes": [
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lnd",
                },
            ],
            "ports": [],
            "mode": "native",
        },
        "raiden": {
            "image": "exchangeunion/raiden",
            "volumes": [
                {
                    "host": "$data_dir/raiden",
                    "container": "/root/.raiden",
                },
            ],
            "ports": [],
            "mode": "native",
        },
        "xud": {
            "image": "exchangeunion/xud",
            "volumes": [
                {
                    "host": "$data_dir/xud",
                    "container": "/root/.xud",
                },
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lndbtc",
                },
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lndltc",
                },
                {
                    "host": "$data_dir/raiden",
                    "container": "/root/.raiden",
                },
                {
                    "host": "/",
                    "container": "/mnt/hostfs",
                },
            ],
            "ports": [PortPublish("18885")],
            "mode": "native",
        }
    },
    "mainnet": {
        "bitcoind": {
            "image": "exchangeunion/bitcoind",
            "volumes": [
                {
                    "host": "$data_dir/bitcoind",
                    "container": "/root/.bitcoin",
                }
            ],
            "ports": [],
            "mode": "native",  # external, neutrino
            "external_rpc_host": "127.0.0.1",
            "external_rpc_port": 8332,
            "external_rpc_user": "xu",
            "external_rpc_password": "xu",
            "external_zmqpubrawblock": "127.0.0.1:28332",
            "external_zmqpubrawtx": "127.0.0.1:28333",
        },
        "litecoind": {
            "image": "exchangeunion/litecoind",
            "volumes": [
                {
                    "host": "$data_dir/litecoind",
                    "container": "/root/.litecoin",
                }
            ],
            "ports": [],
            "mode": "native",  # external, neutrino
            "external_rpc_host": "127.0.0.1",
            "external_rpc_port": 9332,
            "external_rpc_user": "xu",
            "external_rpc_password": "xu",
            "external_zmqpubrawblock": "127.0.0.1:29332",
            "external_zmqpubrawtx": "127.0.0.1:29333",
        },
        "geth": {
            "image": "exchangeunion/geth",
            "volumes": [
                {
                    "host": "$data_dir/geth",
                    "container": "/root/.ethereum",
                }
            ],
            "ports": [],
            "mode": "native",  # external, infura
            "external_rpc_host": "127.0.0.1",
            "external_rpc_port": 8545,
            "infura_project_id": None,
            "infura_project_secret": None,
        },
        "lndbtc": {
            "image": "exchangeunion/lnd",
            "volumes": [
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lnd",
                },
            ],
            "ports": [],
            "mode": "native",
        },
        "lndltc": {
            "image": "exchangeunion/lnd",
            "volumes": [
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lnd",
                },
            ],
            "ports": [],
            "mode": "native",
        },
        "raiden": {
            "image": "exchangeunion/raiden",
            "volumes": [
                {
                    "host": "$data_dir/raiden",
                    "container": "/root/.raiden",
                },
            ],
            "ports": [],
            "mode": "native",
        },
        "xud": {
            "image": "exchangeunion/xud",
            "volumes": [
                {
                    "host": "$data_dir/xud",
                    "container": "/root/.xud",
                },
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lndbtc",
                },
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lndltc",
                },
                {
                    "host": "$data_dir/raiden",
                    "container": "/root/.raiden",
                },
                {
                    "host": "/",
                    "container": "/mnt/hostfs",
                },
            ],
            "ports": [PortPublish("8885")],
            "mode": "native",
        }
    }
}


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

        self.nodes = networks[self.network]

        self.args = None

    def parse(self):
        self.parse_command_line_arguments()
        self.network_dir = "{}/{}".format(self.home_dir, self.network)
        # parse general configurations
        self.parse_config_file()
        self.apply_general_args()
        # parse network specific configurations
        self.network_dir = self.ensure_network_dir()
        self.parse_network_config_file()
        self.apply_network_args()

        for node in self.nodes.values():
            for v in node["volumes"]:
                v["host"] = self.expand_vars(v["host"])

        node_json = self.get_nodes_json()
        for key, value in self.nodes.items():
            image = node_json[key]["image"]
            value["image"] = image

    def ensure_home_dir(self):
        home = os.environ["HOST_HOME"]
        home_dir = home + "/.xud-docker"
        hostfs_dir = get_hostfs_file(home_dir)
        if os.path.exists(hostfs_dir):
            if not os.path.isdir(hostfs_dir):
                raise InvalidHomeDir("{} is not a directory".format(home_dir))
            else:
                if not os.access(hostfs_dir, os.R_OK):
                    raise InvalidHomeDir("{} is not readable".format(home_dir))
                if not os.access(hostfs_dir, os.W_OK):
                    raise InvalidHomeDir("{} is not writable".format(home_dir))
        else:
            os.mkdir(hostfs_dir)
        return home_dir

    def ensure_network_dir(self):
        network_dir = normalize_path(self.network_dir)
        hostfs_dir = get_hostfs_file(network_dir)
        if os.path.exists(hostfs_dir):
            if not os.path.isdir(hostfs_dir):
                raise InvalidNetworkDir("{} is not a directory".format(network_dir))
            else:
                if not os.access(hostfs_dir, os.R_OK):
                    raise InvalidNetworkDir("{} is not readable".format(network_dir))
                if not os.access(hostfs_dir, os.W_OK):
                    raise InvalidNetworkDir("{} is not writable".format(network_dir))
        else:
            os.makedirs(hostfs_dir)

        if not os.path.exists(hostfs_dir + "/logs"):
            os.mkdir(hostfs_dir + "/logs")
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
        parser.add_argument("--nodes-json")
        parser.add_argument("--expose-ports")

        parser.add_argument("--bitcoind.mode")
        parser.add_argument("--litecoind.mode")
        parser.add_argument("--geth.mode")

        self.args = parser.parse_args()
        self.logger.info("[Config] Parsed command-line arguments: %r", self.args)

    def apply_general_args(self):
        if hasattr(self.args, "branch"):
            self.branch = self.args.branch

        if hasattr(self.args, "disable_update"):
            self.disable_update = True

        if hasattr(self.args, "external_ip"):
            self.external_ip = self.args.external_ip

    def apply_network_args(self):
        if hasattr(self.args, f"{self.network}_dir"):
            self.network_dir = getattr(self.args, f"{self.network}_dir")

        if hasattr(self.args, "bitcoin_neutrino"):
            if "bitcoind" in self.nodes:
                self.nodes["bitcoind"]["mode"] = "neutrino"

        if hasattr(self.args, "litecoin_neutrino"):
            if "litecoind" in self.nodes:
                self.nodes["litecoind"]["mode"] = "neutrino"

        if hasattr(self.args, "expose_ports"):
            value = self.args.expose_ports
            parts = value.split(",")
            p = re.compile("^(.*)/(.*)$")
            for part in parts:
                part = part.strip()
                m = p.match(part)
                if m:
                    name = m.group(1)
                    port = m.group(2)
                    if name in self.nodes:
                        ports = self.nodes[name]["ports"]
                        port = PortPublish(port)
                        if port not in ports:
                            ports.append(port)
                    else:
                        raise CommandLineArgumentValueError("--expose-ports {}: No such node: {}".format(value, name))
                else:
                    raise CommandLineArgumentValueError("--expose-ports {}: Syntax error: {}".format(value, part))

    def parse_config_file(self):
        network = self.network
        config_file = get_hostfs_file(f"{self.home_dir}/xud-docker.conf")
        sample_config_file = get_hostfs_file(f"{self.home_dir}/sample-xud-docker.conf")
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

    def update_volume(self, volumes, container_dir, host_dir):
        target = [v for v in volumes if v["container_dir"] == container_dir]
        if len(target) == 0:
            volumes.append({
                "host": host_dir,
                "container": container_dir,
            })
        else:
            target = target[0]
            target["host_dir"] = host_dir

    def update_ports(self, node, parsed):
        if "expose-ports" in parsed:
            value = parsed["expose-ports"]
            for p in value:
                p = PortPublish(str(p))
                if p not in node["ports"]:
                    node["ports"].append(p)

    def update_bitcoind_kind(self, node, parsed, litecoin=False):
        if "external" in parsed:
            print("Warning: Using deprecated option \"external\". Please use \"mode\" instead.")
            if parsed["external"]:
                node["mode"] = "external"

        if "neutrino" in parsed:
            print("Warning: Using deprecated option \"neutrino\". Please use \"mode\" instead.")
            if parsed["neutrino"]:
                node["mode"] = "neutrino"

        if "mode" in parsed:
            value = parsed["mode"]
            if value not in ["native", "external", "neutrino"]:
                raise NetworkConfigFileValueError("Invalid value of option \"mode\": {}".format(value))
            node["mode"] = value

        if litecoin:
            opt_mode = "litecoind.mode"
        else:
            opt_mode = "bitcoind.mode"

        if hasattr(self.args, opt_mode):
            value = getattr(self.args, opt_mode)
            if value not in ["native", "external", "neutrino"]:
                raise CommandLineArgumentValueError("Invalid value of option \"--{}\": {}".format(opt_mode, value))
            node["mode"] = value

        if node["mode"] == "external":
            if "rpc-host" in parsed:
                value = parsed["rpc-host"]
                node["external_rpc_host"] = value
            if "rpc-port" in parsed:
                value = parsed["rpc-port"]
                try:
                    node["external_rpc_port"] = int(value)
                except ValueError:
                    raise NetworkConfigFileValueError("Invalid value of option \"rpc-port\": " + value)
            if "rpc-user" in parsed:
                value = parsed["rpc-user"]
                node["external_rpc_user"] = value
            if "rpc-password" in parsed:
                value = parsed["rpc-password"]
                node["external_rpc_password"] = value
            if "zmqpubrawblock" in parsed:
                value = parsed["zmqpubrawblock"]
                node["external_zmqpubrawblock"] = value
            if "zmqpubrawtx" in parsed:
                value = parsed["zmqpubrawtx"]
                node["external_zmqpubrawtx"] = value

    def update_bitcoind(self, parsed):
        """Update bitcoind related configurations from parsed TOML bitcoind section
        :param parsed: Parsed bitcoind TOML section
        """
        node = self.nodes["bitcoind"]
        if "dir" in parsed:
            value = parsed["dir"]
            self.update_volume(node["volumes"], "/root/.bitcoin", value)

        self.update_ports(node, parsed)

        self.update_bitcoind_kind(node, parsed)

    def update_litecoind(self, parsed):
        """Update litecoind related configurations from parsed TOML litecoind section
        :param parsed: Parsed geth TOML section
        """
        node = self.nodes["litecoind"]
        if "dir" in parsed:
            value = parsed["dir"]
            self.update_volume(node["volumes"], "/root/.litecoin", value)

        self.update_ports(node, parsed)

        self.update_bitcoind_kind(node, parsed, litecoin=True)

    def update_geth(self, parsed):
        """Update geth related configurations from parsed TOML geth section
        :param parsed: Parsed geth TOML section
        """
        node = self.nodes["geth"]
        if "dir" in parsed:
            value = parsed["dir"]
            self.update_volume(node["volumes"], "/root/.ethereum", value)

        if "ancient-chaindata-dir" in parsed:
            value = parsed["ancient-chaindata-dir"]
            # TODO backward compatible with /root/.ethereum/chaindata
            if self.network == "mainnet":
                host_dir = "/root/.ethereum/chaindata/ancient"
            else:
                host_dir = "/root/.ethereum/testnet/chaindata/ancient"
            self.update_volume(node["volumes"], host_dir, value)

        self.update_ports(node, parsed)

        if "external" in parsed:
            print("Warning: Using deprecated option \"external\". Please use \"mode\" instead.")
            if parsed["external"]:
                node["mode"] = "external"

        if "infura-project-id" in parsed:
            if "mode" not in parsed:
                print("Warning: Please use option \"mode\" to specify Infura usage.")
                node["mode"] = "infura"

        if "mode" in parsed:
            value = parsed["mode"]
            if value not in ["native", "external", "infura"]:
                raise NetworkConfigFileValueError("Invalid value of option \"mode\": {}" + value)
            node["mode"] = value

        if hasattr(self.args, "geth.mode"):
            value = getattr(self.args, "geth.mode")
            if value not in ["native", "external", "infura"]:
                raise CommandLineArgumentValueError("Invalid value of option \"--geth.mode\": {}".format(value))
            node["mode"] = value

        if node["mode"] == "external":
            if "rpc-host" in parsed:
                value = parsed["rpc-host"]
                node["external_rpc_host"] = value
            if "rpc-port" in parsed:
                value = parsed["rpc-port"]
                try:
                    node["external_rpc_port"] = int(value)
                except ValueError:
                    raise NetworkConfigFileValueError("Invalid value of option \"rpc-port\": " + value)
        elif node["mode"] == "infura":
            if "infura-project-id" in parsed:
                value = parsed["infura-project-id"]
                node["infura_project_id"] = value
            if "infura-project-secret" in parsed:
                value = parsed["infura-project-secret"]
                node["infura_project_secret"] = value

    def update_lndbtc(self, parsed):
        """Update lndbtc related configurations from parsed TOML lndbtc section
        :param parsed: Parsed lndbtc TOML section
        """
        node = self.nodes["lndbtc"]
        self.update_ports(node, parsed)

    def update_lndltc(self, parsed):
        """Update lndltc related configurations from parsed TOML lndltc section
        :param parsed: Parsed lndltc TOML section
        """
        node = self.nodes["lndltc"]
        self.update_ports(node, parsed)

    def update_raiden(self, parsed):
        """Update raiden related configurations from parsed TOML raiden section
        :param parsed: Parsed raiden TOML section
        """
        node = self.nodes["raiden"]
        self.update_ports(node, parsed)

    def update_xud(self, parsed):
        """Update xud related configurations from parsed TOML xud section
        :param parsed: Parsed xud TOML section
        """
        node = self.nodes["xud"]
        self.update_ports(node, parsed)

    def update_ltcd(self, parsed):
        """Update ltcd related configurations from parsed TOML ltcd section
        :param parsed: Parsed ltcd TOML section
        """
        node = self.nodes["ltcd"]
        self.update_ports(node, parsed)

    def parse_network_config_file(self):
        network = self.network
        config_file = get_hostfs_file(f"{self.network_dir}/{network}.conf")
        sample_config_file = get_hostfs_file(f"{self.network_dir}/sample-{network}.conf")
        try:
            copyfile(os.path.dirname(__file__) + f'/{network}.conf', sample_config_file)
            with open(config_file) as f:
                parsed = toml.load(f)
                self.logger.info("[Config] Parsed TOML file %s: %r", config_file, parsed)

                if "backup-dir" in parsed and len(parsed["backup-dir"].strip()) > 0:
                    self.backup_dir = parsed["backup-dir"]

                if "bitcoind" in parsed:
                    self.update_bitcoind(parsed["bitcoind"])

                if "litecoind" in parsed:
                    self.update_litecoind(parsed["litecoind"])

                if "geth" in parsed:
                    self.update_geth(parsed["geth"])

                if "lndbtc" in parsed:
                    self.update_lndbtc(parsed["lndbtc"])

                if "lndltc" in parsed:
                    self.update_lndltc(parsed["lndltc"])

                if "raiden" in parsed:
                    self.update_raiden(parsed["raiden"])

                if "xud" in parsed:
                    self.update_xud(parsed["xud"])

                if "ltcd" in parsed:
                    self.update_ltcd(parsed["ltcd"])

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

    def expand_vars(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            if "$home_dir" in value:
                value = value.replace("$home_dir", self.home_dir)
            if f"${self.network}_dir" in value:
                value = value.replace(f"${self.network}_dir", self.network_dir)
            if "$data_dir" in value:
                value = value.replace("$data_dir", self.network_dir + "/data")
        return value

    @property
    def logfile(self):
        if self.network_dir:
            network = self.network
            suffix = os.environ["LOG_TIMESTAMP"]
            return f"{self.network_dir}/logs/{network}-{suffix}.log"
        return None

    def get_nodes_json(self):
        if hasattr(self.args, "nodes_json"):
            f = get_hostfs_file(normalize_path(self.args.nodes_json))
            return json.load(open(f))[self.network]

        try:
            r = urlopen(f"https://raw.githubusercontent.com/ExchangeUnion/xud-docker/{self.branch}/nodes.json")
            return json.load(r)[self.network]
        except:
            raise NodesJsonMissing()
