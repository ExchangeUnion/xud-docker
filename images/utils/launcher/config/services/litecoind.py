from __future__ import annotations
from typing import TYPE_CHECKING
from .abc import Service, ServiceOptions
from .bitcoind import Bitcoind
if TYPE_CHECKING:
    from ..presets import Preset


class Litecoind(Bitcoind):
    def __init__(self, preset: Preset, name: str = "litecoind", image: str = "exchangeunion/litecoind"):
        super().__init__(preset, name, image)
