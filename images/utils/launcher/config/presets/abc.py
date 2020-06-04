from __future__ import annotations
from typing import TYPE_CHECKING, Type
from abc import ABC, abstractmethod
from .update import UpdateManager

if TYPE_CHECKING:
    from ..config import Config, ParseResult
    from ..services import Service
    from ..options import BackupDirOption
    from ..types import ArgumentParser
    from ..docker import Network


class PresetOptions:
    def __init__(self, preset: Preset):
        self.backup_dir = BackupDirOption(preset)


class Preset(ABC):
    services: [Service]
    docker_network: Network

    def __init__(self, config: Config):
        self.config = config
        self.services = []
        self.docker_network = config.docker_factory.create_image(f"{self.prefix}_default")
        self._update_manager = UpdateManager(self)
        self._options = PresetOptions(self)

    @abstractmethod
    @property
    def prefix(self) -> str:
        pass

    def service(self, name: str) -> Service:
        return [s for s in self.services if s.name == name][0]

    def configure(self, parser: ArgumentParser) -> None:
        for svc in self.services:
            svc.configure(parser)

    def parse(self, result: ParseResult) -> None:
        self._options.backup_dir.parse(result)
        for svc in self.services:
            svc.parse(result)

    def up(self) -> None:
        self.docker_network.create()
        for svc in self.services:
            svc.create()
        for svc in self.services:
            svc.start()

    def down(self) -> None:
        for svc in self.services:
            svc.stop()
        for svc in self.services:
            svc.destroy()
        self.docker_network.destroy()

    def update(self) -> None:
        self._update_manager.update()
