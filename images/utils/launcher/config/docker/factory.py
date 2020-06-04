from __future__ import annotations
from typing import TYPE_CHECKING
import docker
if TYPE_CHECKING:
    from .network import Network
    from .image import Image
    from .container import Container


class DockerClientFactory:
    shared_client: docker.DockerClient
    _clients: [docker.DockerClient]

    def __init__(self):
        self.shared_client = docker.from_env()
        self._clients = []

    def create_client(self):
        client = docker.from_env()
        self._clients.append(client)
        return client

    def destroy(self):
        for client in self._clients:
            client.close()


class DockerFactory:
    client_factory: DockerClientFactory
    _networks: [Network]
    _containers: [Container]
    _images: [Image]

    def __init__(self, client_factory: DockerClientFactory):
        self.client_factory = client_factory
        self._networks = []
        self._images = []
        self._containers = []

    def create_network(self, name: str) -> Network:
        network = Network(self.client_factory, name)
        self._networks.append(network)
        return network

    def create_image(self, name: str) -> Image:
        image = Image(self.client_factory, name)
        self._images.append(image)
        return image

    def create_container(self, name: str) -> Container:
        container = Container(self.client_factory, name)
        self._containers.append(container)
        return container
