from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import Config, ParseResult
    from ..services import Service
    from ..presets import Preset


class Option(metaclass=ABCMeta):
    def __init__(self, config: Config):
        self.config = config
        self.value = None

    @abstractmethod
    def parse(self, result: ParseResult):
        pass

    @abstractmethod
    def configure(self, parser):
        pass


class ServiceOption(Option, metaclass=ABCMeta):
    def __init__(self, service: Service):
        super().__init__(service.preset.config)
        self.service = service


class PresetOption(Option, metaclass=ABCMeta):
    def __init__(self, preset: Preset):
        super().__init__(preset.config)
        self.preset = preset
