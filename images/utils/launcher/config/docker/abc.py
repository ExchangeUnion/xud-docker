from __future__ import annotations
from typing import TYPE_CHECKING, Protocol
import docker
if TYPE_CHECKING:
    from .factory import DockerClientFactory


class DockerSupport:
    def __init__(self, factory: DockerClientFactory):
        self._factory = factory

    @property
    def client(self) -> docker.DockerClient:
        return self._factory.shared_client
