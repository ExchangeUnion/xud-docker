from __future__ import annotations
from typing import TYPE_CHECKING
from .abc import DockerSupport
if TYPE_CHECKING:
    from .factory import DockerClientFactory


class Network(DockerSupport):
    def __init__(self, factory: DockerClientFactory, name: str):
        super().__init__(factory)
        self.name = name

    def create(self) -> None:
        pass

    def destroy(self) -> None:
        pass
