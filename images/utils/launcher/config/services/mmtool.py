from __future__ import annotations
from typing import TYPE_CHECKING
from .abc import Service
if TYPE_CHECKING:
    from ..presets import Preset


class Mmtools(Service):
    def __init__(self, preset: Preset, name: str = "mmtools", image: str = "exchangeunion/mmtools"):
        super().__init__(preset, name, image)
