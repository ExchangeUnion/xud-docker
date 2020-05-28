from enum import Enum

from .image import Image


class ContainerStatus(Enum):
    UP_TO_DATE = 0
    DIFF = 1
    MISSING = 2


class Container:
    def __init__(self, name: str, image: Image):
        self.name = name
        self.image = image

    @property
    def status(self) -> ContainerStatus:
        return ContainerStatus.UP_TO_DATE
