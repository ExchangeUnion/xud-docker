from __future__ import annotations
from typing import TYPE_CHECKING
from .lnd import Lnd
if TYPE_CHECKING:
    from ..presets import Preset


class Lndbtc(Lnd):
    def __init__(self, preset: Preset, name: str = "lndbtc", image: str = "exchangeunion/lnd"):
        super().__init__(preset, name, image)
