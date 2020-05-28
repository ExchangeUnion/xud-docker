from .container import Container
from .image import Image
from .docker import DockerTemplate


class Service:
    def __init__(self, branch: str, docker_template: DockerTemplate, name: str, image: str, container: str):
        self.name = name
        self.image = Image(branch, docker_template, image)
        self.container = Container(container, self.image)
