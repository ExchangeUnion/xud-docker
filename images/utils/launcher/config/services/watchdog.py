from __future__ import annotations
from typing import TYPE_CHECKING
from .abc import Service
if TYPE_CHECKING:
    from ..presets import Preset


class Watchdog(Service):
    def __init__(self, preset: Preset, name: str = "watchdog", image: str = "exchangeunion/watchdog"):
        super().__init__(preset, name, image)
