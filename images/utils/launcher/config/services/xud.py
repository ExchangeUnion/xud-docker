from __future__ import annotations
from typing import TYPE_CHECKING
from .abc import Service
if TYPE_CHECKING:
    from ..presets import Preset


class Xud(Service):
    def __init__(self, preset: Preset, name: str = "xud", image: str = "exchangeunion/xud"):
        super().__init__(preset, name, image)
