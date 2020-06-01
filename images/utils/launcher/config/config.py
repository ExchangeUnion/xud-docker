from __future__ import annotations

from typing import TYPE_CHECKING
import argparse
import logging
from logging.handlers import TimedRotatingFileHandler
import os

import toml

from ..utils import get_hostfs_file, ArgumentParser, ArgumentError
from ..errors import FatalError
from .loader import ConfigLoader



from .options import BranchOption, DisableUpdateOption, ExternalIpOption, NetworkOption, \
    HomeDirOption, SimnetDirOption, TestnetDirOption, MainnetDirOption, BackupDirOption, \
    EthProvidersOption
from .presets import SimnetPreset, TestnetPreset, MainnetPreset

if TYPE_CHECKING:
    from .options import Option
    from .presets import Preset


class ParseResult:
    def __init__(self):
        self.general_conf = None
        self.preset_conf = None
        self.command_line_args = None


class ConfigOptions:
    def __init__(self, config: Config):
        self.branch = BranchOption(config)
        self.network = NetworkOption(config)
        self.disable_update = DisableUpdateOption(config)
        self.external_ip = ExternalIpOption(config)
        self.simnet_dir = SimnetDirOption(config)
        self.testnet_dir = TestnetDirOption(config)
        self.mainnet_dir = MainnetDirOption(config)
        self.backup_dir = BackupDirOption(config)

    def configure(self, parser: ArgumentParser):
        self.branch.configure(parser)
        self.disable_update.configure(parser)
        self.external_ip.configure(parser)
        self.network.configure(parser)
        self.simnet_dir.configure(parser)
        self.testnet_dir.configure(parser)
        self.mainnet_dir.configure(parser)


class ConfigPresets:
    def __init__(self, config: Config):
        self.simnet = SimnetPreset(config)
        self.testnet = TestnetPreset(config)
        self.mainnet = MainnetPreset(config)

    def configure(self, parser: ArgumentParser):
        self.simnet.configure(parser)
        self.testnet.configure(parser)
        self.mainnet.configure(parser)


class Config:
    def __init__(self, loader: ConfigLoader):
        self._logger = logging.getLogger("launcher.Config")
        self._loader = loader
        self._options = ConfigOptions(self)
        self._presets = ConfigPresets(self)
        parser = ArgumentParser(argument_default=argparse.SUPPRESS, prog="launcher")
        self._options.configure(parser)
        self._presets.configure(parser)
        self._parse(parser)

    @property
    def general_conf_file(self):
        return f"{self.home_dir}/xud-docker.conf"

    @property
    def preset(self) -> Preset:
        network = self._options.network.value
        return getattr(self._presets, network)

    @property
    def home_dir(self):
        host_home = os.environ["HOST_HOME"]
        return f"{host_home}/.xud-docker"

    @property
    def preset_dir(self):
        network = self._options.network.value
        network_dir = getattr(self._options, f"{network}_dir").value
        if not network_dir:
            network_dir = f"{self.home_dir}/{self.preset.prefix}"
        return network_dir

    @property
    def preset_conf_file(self):
        return f"{self.preset_dir}/{self.preset.prefix}.conf"

    @property
    def logfile(self):
        return f"{self.preset_dir}/logs/{self.preset.prefix}.conf"

    def _parse(self, parser):
        result = ParseResult()

        try:
            args, unknown = parser.parse_known_args()
            result.command_line_args = args
            self._logger.info("Parsed command-line arguments: %r", args)
        except ArgumentError as e:
            raise FatalError("Failed to parse command-line arguments: %s" % e) from e

        self._options.branch.parse(result)
        self._options.network.parse(result)
        self._options.external_ip.parse(result)
        self._options.disable_update.parse(result)

        try:
            parsed = toml.load(self._loader.open(self.general_conf_file))
            result.general_conf = parsed
            self._logger.info("Parsed xud-docker.conf: %r", parsed)
        except toml.TomlDecodeError as e:
            raise FatalError("Failed to parse xud-docker.conf: %s" % e) from e

        self._options.simnet_dir.parse(result)
        self._options.testnet_dir.parse(result)
        self._options.mainnet_dir.parse(result)

        try:
            parsed = toml.loads(self._loader.open(self.preset_conf_file))
            self.network_config_file = parsed
            self._logger.info("Parsed %s.conf: %r", self.preset.prefix, parsed)
        except Exception as e:
            raise FatalError("Failed to parse %s.conf: %s" % (self.preset.prefix, e)) from e

        self.preset.parse(result)
