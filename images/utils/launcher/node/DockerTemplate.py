import docker
import docker.errors
from docker.models.containers import Container
from typing import Optional


class DockerTemplate:
    def __init__(self):
        self.client = docker.from_env()

    def get_container(self, name: str) -> Optional[Container]:
        try:
            return self.client.containers.get(name)
        except docker.errors.NotFound:
            return None
