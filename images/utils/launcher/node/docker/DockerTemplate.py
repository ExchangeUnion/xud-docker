from __future__ import annotations

from datetime import datetime
from logging import getLogger
from typing import TYPE_CHECKING, Optional

import docker
import docker.errors

from .DockerClientFactory import DockerClientFactory
from .DockerRegistryClient import DockerRegistryClient
from .ImageMetadata import ImageMetadata

if TYPE_CHECKING:
    pass

__all__ = ["DockerTemplate"]

TOKEN_URL = "https://auth.docker.io/token"
REGISTRY_URL = "https://registry-1.docker.io"

logger = getLogger(__name__)


class DockerTemplate:
    def __init__(self, factory: DockerClientFactory):
        self.docker_client = factory.shared_client
        # TODO get registry URLs from docker_client.info()
        self.registry_client = DockerRegistryClient(token_url=TOKEN_URL, registry_url=REGISTRY_URL)

    def get_registry_image_metadata(self, repo: str, tag: str) -> Optional[ImageMetadata]:
        return self.registry_client.get_image_metadata(repo, tag)

    def get_local_image_metadata(self, repo: str, tag: str) -> Optional[ImageMetadata]:
        try:
            name = "{}:{}".format(repo, tag)
            image = self.docker_client.images.get(name)
            digest = image.id
            labels = image.labels
            created_at = datetime.strptime(labels["com.exchangeunion.image.created"], "%Y-%m-%dT%H:%M:%SZ")
            metadata = ImageMetadata(
                repo=repo,
                tag=tag,
                digest=digest,
                revision=labels["com.exchangeunion.image.revision"],
                application_revision=labels["com.exchangeunion.application.revision"],
                created_at=created_at,
            )
            logger.debug("Fetched image %s:%s local metadata: %r\n%s\n%s\n%r", repo, tag, metadata, digest, image.id,
                         image)
            return metadata
        except docker.errors.ImageNotFound:
            return None

    def get_container(self, name):
        try:
            return self.docker_client.containers.get(name)
        except docker.errors.NotFound:
            return None

    def pull_image(self, repo, tag):
        self.docker_client.images.pull(repo, tag)

    def get_image(self, name):
        return self.docker_client.images.get(name)
