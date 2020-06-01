import argparse
import logging
from logging.handlers import TimedRotatingFileHandler
import os
import re

import toml

from ..utils import normalize_path, get_hostfs_file, ArgumentParser, ArgumentError
from ..errors import FatalError
from .template import nodes_config, general_config, PortPublish
from .loader import ConfigLoader


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

        self.eth_providers = general_config[self.network]["eth_providers"]

        self.nodes = nodes_config[self.network]

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
        parser.add_argument("--xud.preserve-config", action="store_true")
        parser.add_argument("--lndbtc.preserve-config", action="store_true")
        parser.add_argument("--lndltc.preserve-config", action="store_true")

        parser.add_argument("--bitcoind.mode")
        parser.add_argument("--bitcoind.rpc-host")
        parser.add_argument("--bitcoind.rpc-port", type=int)
        parser.add_argument("--bitcoind.rpc-user")
        parser.add_argument("--bitcoind.rpc-password")
        parser.add_argument("--bitcoind.zmqpubrawblock")
        parser.add_argument("--bitcoind.zmqpubrawtx")
        parser.add_argument("--bitcoind.expose-ports")

        parser.add_argument("--litecoind.mode")
        parser.add_argument("--litecoind.rpc-host")
        parser.add_argument("--litecoind.rpc-port", type=int)
        parser.add_argument("--litecoind.rpc-user")
        parser.add_argument("--litecoind.rpc-password")
        parser.add_argument("--litecoind.zmqpubrawblock")
        parser.add_argument("--litecoind.zmqpubrawtx")
        parser.add_argument("--litecoind.expose-ports")

        parser.add_argument("--geth.mode")
        parser.add_argument("--geth.rpc-host")
        parser.add_argument("--geth.rpc-port", type=int)
        parser.add_argument("--geth.infura-project-id")
        parser.add_argument("--geth.infura-project-secret")
        parser.add_argument("--geth.expose-ports")

        parser.add_argument("--lndbtc.expose-ports")
        parser.add_argument("--lndltc.expose-ports")
        parser.add_argument("--connext.expose-ports")
        parser.add_argument("--xud.expose-ports")

        try:
            self.args = parser.parse_args()
            self.logger.info("Parsed command-line arguments: %r", self.args)
        except Exception as e:
            raise FatalError("Failed to parse command-line arguments: %s" % e) from e

    def parse_general_config(self):
        network = self.network

        try:
            parsed = toml.loads(self.loader.load_general_config(self.home_dir))
            self.logger.info("Parsed xud-docker.conf: %r", parsed)
        except Exception as e:
            raise FatalError("Failed to parse xud-docker.conf: %s" % e) from e

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
        option = "{}.expose-ports".format(node["name"])
        if option in self.args:
            value = self.args["expose-ports"]
            for p in value.split(","):
                p = PortPublish(p.strip())
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
            if value not in ["native", "external", "neutrino", "light"]:
                raise FatalError("Invalid value of option \"mode\": {}".format(value))
            node["mode"] = value

        if node["name"] == "litecoind":
            opt_prefix = "litecoind"
        else:
            opt_prefix = "bitcoind"

        opt = "{}.mode".format(opt_prefix)
        if hasattr(self.args, opt):
            value = getattr(self.args, opt)
            if value not in ["native", "external", "neutrino", "light"]:
                raise FatalError("Invalid value of option \"--{}\": {}".format(opt, value))
            node["mode"] = value

        if node["mode"] == "external":
            if "rpc-host" in parsed:
                value = parsed["rpc-host"]
                # TODO rpc-host value validation
                node["external_rpc_host"] = value
            opt = "{}.rpc-host".format(opt_prefix)
            if hasattr(self.args, opt):
                value = getattr(self.args, opt)
                node["external_rpc_host"] = value

            if "rpc-port" in parsed:
                value = parsed["rpc-port"]
                try:
                    node["external_rpc_port"] = int(value)
                except ValueError:
                    raise FatalError("Invalid value of option \"rpc-port\": {}".format(value))
            opt = "{}.rpc-port".format(opt_prefix)
            if hasattr(self.args, opt):
                value = getattr(self.args, opt)
                try:
                    node["external_rpc_port"] = int(value)
                except ValueError:
                    raise FatalError("Invalid value of option \"--{}\": {}".format(opt, value))

            if "rpc-user" in parsed:
                value = parsed["rpc-user"]
                # TODO rpc-user value validation
                node["external_rpc_user"] = value
            opt = "{}.rpc-user".format(opt_prefix)
            if hasattr(self.args, opt):
                value = getattr(self.args, opt)
                node["external_rpc_user"] = value

            if "rpc-password" in parsed:
                value = parsed["rpc-password"]
                # TODO rpc-password value validation
                node["external_rpc_password"] = value
            opt = "{}.rpc-password".format(opt_prefix)
            if hasattr(self.args, opt):
                value = getattr(self.args, opt)
                node["external_rpc_password"] = value

            if "zmqpubrawblock" in parsed:
                value = parsed["zmqpubrawblock"]
                # TODO zmqpubrawblock value validation
                node["external_zmqpubrawblock"] = value
            opt = "{}.zmqpubrawblock".format(opt_prefix)
            if hasattr(self.args, opt):
                value = getattr(self.args, opt)
                node["external_zmqpubrawblock"] = value

            if "zmqpubrawtx" in parsed:
                value = parsed["zmqpubrawtx"]
                # TODO zmqpubrawtx value validation
                node["external_zmqpubrawtx"] = value
            opt = "{}.zmqpubrawtx".format(opt_prefix)
            if hasattr(self.args, opt):
                value = getattr(self.args, opt)
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
            if value not in ["native", "external", "infura", "light"]:
                raise FatalError("Invalid value of option \"mode\": {}" + value)
            node["mode"] = value

        if hasattr(self.args, "geth.mode"):
            value = getattr(self.args, "geth.mode")
            if value not in ["native", "external", "infura", "light"]:
                raise FatalError("Invalid value of option \"--geth.mode\": {}".format(value))
            node["mode"] = value

        if node["mode"] == "external":
            if "rpc-host" in parsed:
                value = parsed["rpc-host"]
                # TODO rpc-host value validation
                node["external_rpc_host"] = value
            opt = "geth.rpc-host"
            if hasattr(self.args, opt):
                value = getattr(self.args, opt)
                node["external_rpc_host"] = value

            if "rpc-port" in parsed:
                value = parsed["rpc-port"]
                try:
                    node["external_rpc_port"] = int(value)
                except ValueError:
                    raise FatalError("Invalid value of option \"rpc-port\": {}".format(value))
            opt = "geth.rpc-port"
            if hasattr(self.args, opt):
                value = getattr(self.args, opt)
                try:
                    node["external_rpc_port"] = int(value)
                except ValueError:
                    raise FatalError("Invalid value of option \"--{}\": {}".format(opt, value))

        elif node["mode"] == "infura":
            if "infura-project-id" in parsed:
                value = parsed["infura-project-id"]
                # TODO infura-project-id value validation
                node["infura_project_id"] = value
            opt = "geth.infura-project-id"
            if hasattr(self.args, opt):
                value = getattr(self.args, opt)
                node["infura_project_id"] = value

            if "infura-project-secret" in parsed:
                value = parsed["infura-project-secret"]
                # TODO infura-project-secret value validation
                node["infura_project_secret"] = value
            opt = "geth.infura-project-secret"
            if hasattr(self.args, opt):
                value = getattr(self.args, opt)
                node["infura_project_secret"] = value

        if "cache" in parsed:
            value = int(parsed["cache"])
            node["cache"] = value

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
        if self.network in ["simnet", "testnet", "mainnet"]:
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

        try:
            parsed = toml.loads(self.loader.load_network_config(network, self.network_dir))
            self.logger.info("Parsed %s.conf: %r", network, parsed)
        except Exception as e:
            raise FatalError("Failed to parse %s.conf: %s" % (network, e)) from e

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
                        raise FatalError("--expose-ports {}: No such node: {}".format(value, name))
                else:
                    raise FatalError("--expose-ports {}: Syntax error: {}".format(value, part))

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
            return f"{self.network_dir}/logs/{network}.log"
        return None
