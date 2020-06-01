from __future__ import annotations
from typing import TYPE_CHECKING
from .lnd import Lnd
if TYPE_CHECKING:
    from ..presets import Preset


class Lndltc(Lnd):
    def __init__(self, preset: Preset, name: str = "lndltc", image: str = "exchangeunion/lnd"):
        super().__init__(preset, name, image)
