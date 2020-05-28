from typing import Optional
from functools import cached_property
from collections import namedtuple
from enum import Enum

from .errors import ImageNotFound
from .docker import DockerTemplate, ImageMetadata


StatusTuple = namedtuple("StatusTuple", ["status", "using_image"])


class ImageStatus(Enum):
    UP_TO_DATE = 0,
    OUTDATED = 1,
    MISSING = 2,
    NEWER = 3,
    LOCAL = 4,


class Image:
    def __init__(self, branch: str, docker_template: DockerTemplate, name: str):
        self.branch = branch
        self.docker_template = docker_template

        self.name = name
        self.repo, self.tag = name.split(":")

    def _get_metadata(self, local=True) -> Optional[ImageMetadata]:
        branch = self.branch
        if branch == "master":
            repo = self.repo
            tag = self.tag
            metadata = self.docker_template.get_image_metadata(repo, tag, local)
            if metadata:
                return metadata
            return None
        else:
            repo = self.repo
            tag = self.tag + "__" + branch.replace("/", "-")
            metadata = self.docker_template.get_image_metadata(repo, tag, local)
            if metadata:
                return metadata
            tag = self.tag
            metadata = self.docker_template.get_image_metadata(repo, tag, local)
            if metadata:
                return metadata
            return None

    @cached_property
    def registry_image(self) -> Optional[ImageMetadata]:
        return self._get_metadata(local=False)

    @cached_property
    def local_image(self) -> Optional[ImageMetadata]:
        return self._get_metadata(local=True)

    @cached_property
    def status_tuple(self) -> StatusTuple:
        registry_image = self.registry_image
        local_image = self.local_image

        if not registry_image and not local_image:
            raise ImageNotFound(self)

        if not registry_image:
            return StatusTuple(ImageStatus.LOCAL, local_image)

        if not local_image:
            return StatusTuple(ImageStatus.MISSING, registry_image)

        if local_image.digest == registry_image.digest:
            return StatusTuple(ImageStatus.UP_TO_DATE, local_image)
        else:
            if local_image.created_datetime > registry_image.created_datetime:
                return StatusTuple(ImageStatus.NEWER, local_image)
            else:
                return StatusTuple(ImageStatus.OUTDATED, registry_image)

    @property
    def using_image(self) -> Optional[ImageMetadata]:
        return self.status_tuple.using_image

    @property
    def status(self) -> ImageStatus:
        return self.status_tuple.status

    def __str__(self):
        return self.name
