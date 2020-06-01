from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from enum import Enum

if TYPE_CHECKING:
    from .abc import Preset


class UpdateDetails:
    images: [ImageDetails]
    containers: [ContainerDetails]
    network: Optional[NetworkDetails]

    def __init__(self):
        self.images = []
        self.containers = []
        self.network = None


class ImageDetails:
    status: ImageStatus


class ImageStatus(Enum):
    UP_TO_DATE = 0
    OUTDATED = 1
    MISSING = 2
    NEWER = 3
    LOCAL = 4


class ContainerDetails:
    status: ContainerStatus


class ContainerStatus(Enum):
    SAME = 0
    DIFF = 1
    MISSING = 2


class NetworkDetails:
    pass


class UpdateManager:
    def __init__(self, preset: Preset):
        self._preset = preset

    @property
    def update_details(self) -> UpdateDetails:
        return UpdateDetails()

    def pull_image(self, image: ImageDetails) -> None:
        pass

    def recreate_container(self, container: ContainerDetails) -> None:
        pass

    def pristine(self, details: UpdateDetails) -> bool:
        return True

    def update(self) -> None:
        details = self.update_details
        if not details:
            return
        if not self.pristine(details):
            print(details)
            input("Update? [Y/n]")
        # TODO do update: pull images, recreate containers, recreate network
        for image in details.images:
            if image.status == ImageStatus.MISSING or image.status == ImageStatus.OUTDATED:
                self.pull_image(image)

        for container in details.containers:
            if container.status == ContainerStatus.MISSING or container.status == ContainerStatus.DIFF:
                self.recreate_container(container)