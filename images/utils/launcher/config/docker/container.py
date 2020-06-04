from __future__ import annotations
from typing import TYPE_CHECKING
from .abc import DockerSupport
if TYPE_CHECKING:
    from .factory import DockerClientFactory


class Container(DockerSupport):
    def __init__(self, factory: DockerClientFactory, name: str):
        super().__init__(factory)
        self.name = name
        self.command = []
        self.ports = []
        self.volumes = []

    def create(self) -> None:
        pass

    def destroy(self) -> None:
        pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    @property
    def status(self) -> str:
        return "running"

