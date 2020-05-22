import argparse
import logging
from logging.handlers import TimedRotatingFileHandler
import os
from shutil import copyfile
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
        "lndbtc": {
            "name": "lndbtc",
            "image": "exchangeunion/lnd:0.10.0-beta-simnet",
            "volumes": [
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lnd",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
        },
        "lndltc": {
            "name": "lndltc",
            "image": "exchangeunion/lnd:0.9.0-beta-ltc-simnet",
            "volumes": [
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lnd",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
        },
        "connext": {
            "name": "connext",
            "image": "exchangeunion/connext:latest",
            "volumes": [
                {
                    "host": "$data_dir/connext",
                    "container": "/root/.connext",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
        },
        "xud": {
            "name": "xud",
            "image": "exchangeunion/xud:latest",
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
                    "host": "/",
                    "container": "/mnt/hostfs",
                },
            ],
            "ports": [PortPublish("28885")],
            "mode": "native",
            "preserve_config": False,
        }
    },
    "testnet": {
        "bitcoind": {
            "name": "bitcoind",
            "image": "exchangeunion/bitcoind:0.19.1",
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
            "preserve_config": False,
        },
        "litecoind": {
            "name": "litecoind",
            "image": "exchangeunion/litecoind:0.17.1",
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
            "preserve_config": False,
        },
        "geth": {
            "name": "geth",
            "image": "exchangeunion/geth:1.9.14",
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
            "preserve_config": False,
        },
        "lndbtc": {
            "name": "lndbtc",
            "image": "exchangeunion/lnd:0.10.0-beta",
            "volumes": [
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lnd",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
        },
        "lndltc": {
            "name": "lndltc",
            "image": "exchangeunion/lnd:0.9.0-beta-ltc",
            "volumes": [
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lnd",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
        },
        "raiden": {
            "name": "raiden",
            "image": "exchangeunion/raiden:0.100.5a1.dev162-2217bcb",
            "volumes": [
                {
                    "host": "$data_dir/raiden",
                    "container": "/root/.raiden",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
        },
        "xud": {
            "name": "xud",
            "image": "exchangeunion/xud:latest",
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
            "preserve_config": False,
        }
    },
    "mainnet": {
        "bitcoind": {
            "name": "bitcoind",
            "image": "exchangeunion/bitcoind:0.19.1",
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
            "preserve_config": False,
        },
        "litecoind": {
            "name": "litecoind",
            "image": "exchangeunion/litecoind:0.17.1",
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
            "preserve_config": False,
        },
        "geth": {
            "name": "geth",
            "image": "exchangeunion/geth:1.9.14",
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
            "preserve_config": False,
        },
        "lndbtc": {
            "name": "lndbtc",
            "image": "exchangeunion/lnd:0.10.0-beta",
            "volumes": [
                {
                    "host": "$data_dir/lndbtc",
                    "container": "/root/.lnd",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
        },
        "lndltc": {
            "name": "lndltc",
            "image": "exchangeunion/lnd:0.9.0-beta-ltc",
            "volumes": [
                {
                    "host": "$data_dir/lndltc",
                    "container": "/root/.lnd",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
        },
        "raiden": {
            "name": "raiden",
            "image": "exchangeunion/raiden:0.100.5a1.dev162-2217bcb",
            "volumes": [
                {
                    "host": "$data_dir/raiden",
                    "container": "/root/.raiden",
                },
            ],
            "ports": [],
            "mode": "native",
            "preserve_config": False,
        },
        "xud": {
            "name": "xud",
            "image": "exchangeunion/xud:1.0.0-beta.2",
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
            "preserve_config": False,
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


class ConfigLoader:
    def load_general_config(self, home_dir):
        config_file = get_hostfs_file(f"{home_dir}/xud-docker.conf")
        sample_config_file = get_hostfs_file(f"{home_dir}/sample-xud-docker.conf")
        copyfile(os.path.dirname(__file__) + "/xud-docker.conf", sample_config_file)
        if not os.path.exists(config_file):
            copyfile(os.path.dirname(__file__) + f"/xud-docker.conf", config_file)
        with open(config_file) as f:
            return f.read()

    def load_network_config(self, network, network_dir):
        config_file = get_hostfs_file(f"{network_dir}/{network}.conf")
        sample_config_file = get_hostfs_file(f"{network_dir}/sample-{network}.conf")
        copyfile(os.path.dirname(__file__) + f'/{network}.conf', sample_config_file)
        if not os.path.exists(config_file):
            copyfile(os.path.dirname(__file__) + f"/{network}.conf", config_file)
        with open(config_file) as f:
            return f.read()

    def load_lndenv(self, network_dir):
        lndenv = get_hostfs_file(f"{network_dir}/lnd.env")
        try:
            with open(lndenv) as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def ensure_home_dir(self, host_home):
        home_dir = host_home + "/.xud-docker"
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

    def ensure_network_dir(self, network_dir):
        network_dir = normalize_path(network_dir)
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


class Config:
    def __init__(self, loader: ConfigLoader):
        self.logger = logging.getLogger("launcher.Config")

        self.loader = loader

        self.branch = "master"
        self.disable_update = False
        self.external_ip = None
        self.network = os.environ["NETWORK"]

        self.home_dir = self.loader.ensure_home_dir(os.environ["HOST_HOME"])
        self.network_dir = None
        self.backup_dir = None
        self.restore_dir = None

        self.nodes = networks[self.network]

        self.args = None

        self.parse()

    def parse(self):
        self.parse_command_line_arguments()
        self.network_dir = "{}/{}".format(self.home_dir, self.network)
        self.parse_general_config()
        self.network_dir = self.loader.ensure_network_dir(self.network_dir)
        self.parse_network_config()

        for node in self.nodes.values():
            for v in node["volumes"]:
                v["host"] = self.expand_vars(v["host"])

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
        parser.add_argument("--xud.preserve-config", action="store_true")
        parser.add_argument("--lndbtc.preserve-config", action="store_true")
        parser.add_argument("--lndltc.preserve-config", action="store_true")

        self.args = parser.parse_args()
        self.logger.info("Parsed command-line arguments: %r", self.args)

    def parse_general_config(self):
        network = self.network
        parsed = toml.loads(self.loader.load_general_config(self.home_dir))
        self.logger.info("Parsed general config file: %r", parsed)
        key = f"{network}-dir"
        if key in parsed:
            self.network_dir = parsed[key]
        if hasattr(self.args, f"{self.network}_dir"):
            self.network_dir = getattr(self.args, f"{self.network}_dir")

        logs_dir = get_hostfs_file(f"{self.network_dir}/logs")
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir, exist_ok=True)
        logfile = f"{logs_dir}/{self.network}.log"
        fh = TimedRotatingFileHandler(logfile, when="d", interval=1, backupCount=7)
        fmt = "%(asctime)s %(levelname)s %(process)d --- [%(threadName)s] %(name)s: %(message)s"
        fh.setFormatter(logging.Formatter(fmt=fmt))
        logging.getLogger().addHandler(fh)

        if hasattr(self.args, "branch"):
            self.branch = self.args.branch

        if hasattr(self.args, "disable_update"):
            self.disable_update = True

        if hasattr(self.args, "external_ip"):
            self.external_ip = self.args.external_ip

    def update_volume(self, volumes, container_dir, host_dir):
        target = [v for v in volumes if v["container"] == container_dir]
        if len(target) == 0:
            volumes.append({
                "host": host_dir,
                "container": container_dir,
            })
        else:
            target = target[0]
            target["host"] = host_dir

    def update_ports(self, node, parsed):
        if "expose-ports" in parsed:
            value = parsed["expose-ports"]
            for p in value:
                p = PortPublish(str(p))
                if p not in node["ports"]:
                    node["ports"].append(p)

    def update_bitcoind_kind(self, node, parsed):
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

        if node["mode"] == "external":
            if "rpc-host" in parsed:
                value = parsed["rpc-host"]
                # TODO rpc-host value validation
                node["external_rpc_host"] = value
            if "rpc-port" in parsed:
                value = parsed["rpc-port"]
                try:
                    node["external_rpc_port"] = int(value)
                except ValueError:
                    raise NetworkConfigFileValueError("Invalid value of option \"rpc-port\": {}".format(value))
            if "rpc-user" in parsed:
                value = parsed["rpc-user"]
                # TODO rpc-user value validation
                node["external_rpc_user"] = value
            if "rpc-password" in parsed:
                value = parsed["rpc-password"]
                # TODO rpc-password value validation
                node["external_rpc_password"] = value
            if "zmqpubrawblock" in parsed:
                value = parsed["zmqpubrawblock"]
                # TODO zmqpubrawblock value validation
                node["external_zmqpubrawblock"] = value
            if "zmqpubrawtx" in parsed:
                value = parsed["zmqpubrawtx"]
                # TODO zmqpubrawtx value validation
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

        self.update_bitcoind_kind(node, parsed)

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
            self.update_volume(node["volumes"], "/root/.ethereum-ancient-chaindata", value)

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

        if node["mode"] == "external":
            if "rpc-host" in parsed:
                value = parsed["rpc-host"]
                # TODO rpc-host value validation
                node["external_rpc_host"] = value
            if "rpc-port" in parsed:
                value = parsed["rpc-port"]
                try:
                    node["external_rpc_port"] = int(value)
                except ValueError:
                    raise NetworkConfigFileValueError("Invalid value of option \"rpc-port\": {}".format(value))
        elif node["mode"] == "infura":
            if "infura-project-id" in parsed:
                value = parsed["infura-project-id"]
                # TODO infura-project-id value validation
                node["infura_project_id"] = value
            if "infura-project-secret" in parsed:
                value = parsed["infura-project-secret"]
                # TODO infura-project-secret value validation
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

    def update_connext(self, parsed):
        """Update Connext related configurations from parsed TOML raiden section
        :param parsed: Parsed raiden TOML section
        """
        node = self.nodes["connext"]
        self.update_ports(node, parsed)

    def update_raiden(self, parsed):
        """Update raiden related configurations from parsed TOML raiden section
        :param parsed: Parsed raiden TOML section
        """
        if self.network == "simnet":
            return
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

    def parse_network_config(self):
        network = self.network
        parsed = toml.loads(self.loader.load_network_config(network, self.network_dir))
        self.logger.info("Parsed network config file: %r", parsed)

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

        if "connext" in parsed:
            self.update_connext(parsed["connext"])

        if "xud" in parsed:
            self.update_xud(parsed["xud"])

        if "ltcd" in parsed:
            self.update_ltcd(parsed["ltcd"])

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

        # Backward compatible with lnd.env
        lndenv = get_hostfs_file(f"{self.network_dir}/lnd.env")
        try:
            with open(lndenv) as f:
                for line in f.readlines():
                    if "EXTERNAL_IP" in line:
                        parts = line.split("=")
                        self.external_ip = parts[1].strip()
        except FileNotFoundError:
            pass

        if hasattr(self.args, "xud.preserve_config"):
            if "xud" in self.nodes:
                self.nodes["xud"]["preserve_config"] = True

        if hasattr(self.args, "lndbtc.preserve_config"):
            if "lndbtc" in self.nodes:
                self.nodes["lndbtc"]["preserve_config"] = True

        if hasattr(self.args, "lndltc.preserve_config"):
            if "lndltc" in self.nodes:
                self.nodes["lndltc"]["preserve_config"] = True

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
