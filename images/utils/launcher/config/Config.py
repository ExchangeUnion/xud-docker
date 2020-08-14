import argparse
import logging
from logging.handlers import TimedRotatingFileHandler
import os

import toml

from ..utils import get_hostfs_file, ArgumentParser
from ..errors import ConfigError, ConfigErrorScope
from .template import nodes_config, general_config, PortPublish
from .ConfigLoader import ConfigLoader


__all__ = ["Config"]


class Config:
    def __init__(self, loader: ConfigLoader):
        self.logger = logging.getLogger(__name__)

        self.loader = loader

        self.launch_id = os.environ["LAUNCH_ID"]
        self.branch = os.environ["BRANCH"]
        self.network = os.environ["NETWORK"]
        self.silent_upgrade = os.environ["UPGRADE"] == "yes"
        self.dev_mode = os.environ["DEV"] == "true"
        self.host_pwd = os.environ["HOST_PWD"]
        self.host_home = os.environ["HOST_HOME"]
        self.host_home_dir = os.environ["HOST_HOME_DIR"]
        self.host_network_dir = os.environ["HOST_NETWORK_DIR"]

        self.home_dir = "/root/.xud-docker"
        self.network_dir = os.path.join("/root/.xud-docker/", self.network)
        self.logs_dir = os.path.join(self.network_dir, "logs")
        self.logfile = os.path.join(self.logs_dir, f"{self.network}.log")
        self._configure_logging()
        self.data_dir = os.path.join(self.network_dir, "data")
        self.backup_dir = None
        self.restore_dir = None

        self.eth_providers = general_config[self.network]["eth_providers"]

        self.nodes = nodes_config[self.network]

        self.args = None

        self.external_ip = None

        self.parse()

    def parse(self):
        try:
            self.parse_command_line_arguments()
        except Exception as e:
            raise ConfigError(ConfigErrorScope.COMMAND_LINE_ARGS) from e

        if hasattr(self.args, "external_ip"):
            self.external_ip = self.args.external_ip

        try:
            self.parse_network_config()
        except Exception as e:
            conf_file = "{}/{}.conf".format(self.network_dir, self.network)
            raise ConfigError(ConfigErrorScope.NETWORK_CONF, conf_file=conf_file) from e

        for node in self.nodes.values():
            for v in node["volumes"]:
                v["host"] = self.expand_vars(v["host"])

    def parse_command_line_arguments(self):
        parser = ArgumentParser(argument_default=argparse.SUPPRESS, prog="launcher")
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
        parser.add_argument("--geth.cache", type=int)

        parser.add_argument("--lndbtc.expose-ports")
        parser.add_argument("--lndltc.expose-ports")
        parser.add_argument("--connext.expose-ports")
        parser.add_argument("--xud.expose-ports")

        parser.add_argument("--arby.live-cex")
        parser.add_argument("--arby.base-asset")
        parser.add_argument("--arby.quote-asset")
        parser.add_argument("--arby.test-centralized-baseasset-balance")
        parser.add_argument("--arby.test-centralized-quoteasset-balance")
        parser.add_argument("--arby.binance-api-key")
        parser.add_argument("--arby.binance-api-secret")
        parser.add_argument("--arby.margin")
        parser.add_argument("--arby.disabled", nargs='?')

        parser.add_argument("--boltz.disabled", nargs='?')

        parser.add_argument("--webui.disabled", nargs='?')
        parser.add_argument("--webui.expose-ports")

        self.args, _ = parser.parse_known_args()
        self.logger.info("Parsed command-line arguments: %r", self.args)

    def _configure_logging(self):
        fh = TimedRotatingFileHandler(self.logfile, when="d", interval=1, backupCount=7)
        fmt = "%(asctime)s %(levelname)s %(process)d --- [%(threadName)s] %(name)s: %(message)s"
        fh.setFormatter(logging.Formatter(fmt=fmt))
        logging.getLogger().addHandler(fh)

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

    def update_ports(self, node, parsed, mapping=None):
        if "expose-ports" in parsed:
            value = parsed["expose-ports"]
            for p in value:
                if mapping and p in mapping:
                    p = mapping[p]
                p = PortPublish(str(p))
                if p not in node["ports"]:
                    node["ports"].append(p)
        opt = "{}.expose_ports".format(node["name"])
        if hasattr(self.args, opt):
            value = getattr(self.args, opt)
            for p in value.split(","):
                if mapping and p in mapping:
                    p = mapping[p]
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
                raise ValueError("Invalid value of option \"mode\": {}".format(value))
            node["mode"] = value

        if node["name"] == "litecoind":
            opt_prefix = "litecoind"
        else:
            opt_prefix = "bitcoind"

        opt = "{}.mode".format(opt_prefix)
        if hasattr(self.args, opt):
            value = getattr(self.args, opt)
            if value not in ["native", "external", "neutrino", "light"]:
                raise ValueError("Invalid value of option \"--{}\": {}".format(opt, value))
            node["mode"] = value

        if node["mode"] == "external":
            if "rpc-host" in parsed:
                value = parsed["rpc-host"]
                # TODO rpc-host value validation
                node["external_rpc_host"] = value
            opt = "{}.rpc_host".format(opt_prefix)
            if hasattr(self.args, opt):
                value = getattr(self.args, opt)
                node["external_rpc_host"] = value

            if "rpc-port" in parsed:
                value = parsed["rpc-port"]
                try:
                    node["external_rpc_port"] = int(value)
                except ValueError:
                    raise ValueError("Invalid value of option \"rpc-port\": {}".format(value))
            opt = "{}.rpc_port".format(opt_prefix)
            if hasattr(self.args, opt):
                value = getattr(self.args, opt)
                try:
                    node["external_rpc_port"] = int(value)
                except ValueError:
                    raise ValueError("Invalid value of option \"--{}\": {}".format(opt, value))

            if "rpc-user" in parsed:
                value = parsed["rpc-user"]
                # TODO rpc-user value validation
                node["external_rpc_user"] = value
            opt = "{}.rpc_user".format(opt_prefix)
            if hasattr(self.args, opt):
                value = getattr(self.args, opt)
                node["external_rpc_user"] = value

            if "rpc-password" in parsed:
                value = parsed["rpc-password"]
                # TODO rpc-password value validation
                node["external_rpc_password"] = value
            opt = "{}.rpc_password".format(opt_prefix)
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
                raise ValueError("Invalid value of option \"mode\": {}" + value)
            node["mode"] = value

        if hasattr(self.args, "geth.mode"):
            value = getattr(self.args, "geth.mode")
            if value not in ["native", "external", "infura", "light"]:
                raise ValueError("Invalid value of option \"--geth.mode\": {}".format(value))
            node["mode"] = value

        if node["mode"] == "external":
            if "rpc-host" in parsed:
                value = parsed["rpc-host"]
                # TODO rpc-host value validation
                node["external_rpc_host"] = value
            opt = "geth.rpc_host"
            if hasattr(self.args, opt):
                value = getattr(self.args, opt)
                node["external_rpc_host"] = value

            if "rpc-port" in parsed:
                value = parsed["rpc-port"]
                try:
                    node["external_rpc_port"] = int(value)
                except ValueError:
                    raise ValueError("Invalid value of option \"rpc-port\": {}".format(value))
            opt = "geth.rpc_port"
            if hasattr(self.args, opt):
                value = getattr(self.args, opt)
                try:
                    node["external_rpc_port"] = int(value)
                except ValueError:
                    raise ValueError("Invalid value of option \"--{}\": {}".format(opt, value))

        elif node["mode"] == "infura":
            if "infura-project-id" in parsed:
                value = parsed["infura-project-id"]
                # TODO infura-project-id value validation
                node["infura_project_id"] = value
            opt = "geth.infura_project_id"
            if hasattr(self.args, opt):
                value = getattr(self.args, opt)
                node["infura_project_id"] = value

            if "infura-project-secret" in parsed:
                value = parsed["infura-project-secret"]
                # TODO infura-project-secret value validation
                node["infura_project_secret"] = value
            opt = "geth.infura_project_secret"
            if hasattr(self.args, opt):
                value = getattr(self.args, opt)
                node["infura_project_secret"] = value

        if "cache" in parsed:
            value = int(parsed["cache"])
            node["cache"] = value
        opt = "geth.cache"
        if hasattr(self.args, opt):
            value = getattr(self.args, opt)
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
        """Update Connext related configurations from parsed TOML connext section
        :param parsed: Parsed raiden TOML section
        """
        node = self.nodes["connext"]
        self.update_ports(node, parsed)

    def update_xud(self, parsed):
        """Update xud related configurations from parsed TOML xud section
        :param parsed: Parsed xud TOML section
        """
        node = self.nodes["xud"]
        self.update_ports(node, parsed)

    def update_disabled(self, node, parsed, opt):
        if "disabled" in parsed:
            value = parsed["disabled"]
            assert isinstance(value, bool)
            node["disabled"] = value
        if hasattr(self.args, opt):
            value: str = getattr(self.args, opt)
            if value:
                value = value.strip().lower()
            if not value or value == "true" or value == "":
                node["disabled"] = True
            elif value == "false":
                node["disabled"] = False
            else:
                raise ValueError("Invalid value of option \"{}\": {}".format(opt, value))

    def update_arby(self, parsed):
        """Update arby related configurations from parsed TOML arby section
        :param parsed: Parsed xud TOML section
        """
        node = self.nodes["arby"]
        if "test-centralized-baseasset-balance" in parsed:
            if parsed["test-centralized-baseasset-balance"]:
                value = parsed["test-centralized-baseasset-balance"]
                node["test-centralized-baseasset-balance"] = value
        opt = "arby.test_centralized_baseasset_balance"
        if hasattr(self.args, opt):
            value = getattr(self.args, opt)
            if value:
                node["test-centralized-baseasset-balance"] = value

        if "test-centralized-quoteasset-balance" in parsed:
            if parsed["test-centralized-quoteasset-balance"]:
                value = parsed["test-centralized-quoteasset-balance"]
                node["test-centralized-quoteasset-balance"] = value
        opt = "arby.test_centralized_quoteasset_balance"
        if hasattr(self.args, opt):
            value = getattr(self.args, opt)
            if value:
                node["test-centralized-quoteasset-balance"] = value

        if "base-asset" in parsed:
            if parsed["base-asset"]:
                value = parsed["base-asset"]
                node["base-asset"] = value
        opt = "arby.base_asset"
        if hasattr(self.args, opt):
            value = getattr(self.args, opt)
            if value:
                node["base-asset"] = value

        if "quote-asset" in parsed:
            if parsed["quote-asset"]:
                value = parsed["quote-asset"]
                node["quote-asset"] = value
        opt = "arby.quote_asset"
        if hasattr(self.args, opt):
            value = getattr(self.args, opt)
            if value:
                node["quote-asset"] = value

        if "live-cex" in parsed:
            if parsed["live-cex"]:
                value = parsed["live-cex"]
                node["live-cex"] = value
        opt = "arby.live_cex"
        if hasattr(self.args, opt):
            value = getattr(self.args, opt)
            if value:
                node["live-cex"] = value

        if "binance-api-key" in parsed:
            if parsed["binance-api-key"]:
                value = parsed["binance-api-key"]
                node["binance-api-key"] = value
        opt = "arby.binance_api_key"
        if hasattr(self.args, opt):
            value = getattr(self.args, opt)
            if value:
                node["binance-api-key"] = value

        if "binance-api-secret" in parsed:
            if parsed["binance-api-secret"]:
                value = parsed["binance-api-secret"]
                node["binance-api-secret"] = value
        opt = "arby.binance_api_secret"
        if hasattr(self.args, opt):
            value = getattr(self.args, opt)
            if value:
                node["binance-api-secret"] = value

        if "margin" in parsed:
            if parsed["margin"]:
                value = parsed["margin"]
                node["margin"] = value
        opt = "arby.margin"
        if hasattr(self.args, opt):
            value = getattr(self.args, opt)
            if value:
                node["margin"] = value

        self.update_disabled(node, parsed, "arby.disabled")
        self.update_ports(node, parsed)

    def update_boltz(self, parsed):
        """Update webui related configurations from parsed TOML boltz section
        :param parsed: Parsed raiden TOML section
        """
        node = self.nodes["boltz"]
        self.update_disabled(node, parsed, "boltz.disabled")
        self.update_ports(node, parsed)

    def update_webui(self, parsed):
        """Update webui related configurations from parsed TOML webui section
        :param parsed: Parsed raiden TOML section
        """
        node = self.nodes["webui"]
        self.update_disabled(node, parsed, "webui.disabled")
        self.update_ports(node, parsed, mapping={
            "8888": "8888:8080",
            "18888": "18888:8080",
            "28888": "28888:8080",
        })

    def parse_network_config(self):
        network = self.network
        try:
            with open(f"{self.network_dir}/{self.network}.conf") as f:
                conf = f.read()
        except FileNotFoundError:
            conf = ""

        parsed = toml.loads(conf)
        self.logger.info("Parsed %s.conf: %r", network, parsed)

        if "backup-dir" in parsed:
            value = parsed["backup-dir"].strip()
            if len(value) > 0:
                self.backup_dir = value
        opt = "backup_dir"
        if hasattr(self.args, opt):
            value = getattr(self.args, opt).strip()
            if len(value) > 0:
                self.backup_dir = value

        for node in self.nodes.values():
            name = node["name"]
            if name in parsed:
                getattr(self, f"update_{name}")(parsed[name])
            else:
                getattr(self, f"update_{name}")({})

        if hasattr(self.args, "xud.preserve_config"):
            if "xud" in self.nodes:
                self.nodes["xud"]["preserve_config"] = True

        if hasattr(self.args, "lndbtc.preserve_config"):
            if "lndbtc" in self.nodes:
                self.nodes["lndbtc"]["preserve_config"] = True

        if hasattr(self.args, "lndltc.preserve_config"):
            if "lndltc" in self.nodes:
                self.nodes["lndltc"]["preserve_config"] = True

    def expand_vars(self, value: str) -> str:
        if isinstance(value, str):
            if "$home_dir" in value:
                value = value.replace("$home_dir", self.host_home_dir)
            if "$network_dir" in value:
                value = value.replace("$network_dir", self.host_network_dir)
            if "$data_dir" in value:
                value = value.replace("$data_dir", self.host_network_dir + "/data")
        return value
