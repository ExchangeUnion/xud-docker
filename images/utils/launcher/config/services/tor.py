from __future__ import annotations
from typing import TYPE_CHECKING
from .abc import Service
if TYPE_CHECKING:
    from ..presets import Preset


class Tor(Service):
    def __init__(self, preset: Preset, name: str = "tor", image: str = "exchangeunion/tor"):
        super().__init__(preset, name, image)
