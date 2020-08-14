from __future__ import annotations

from datetime import datetime
from logging import getLogger
from typing import TYPE_CHECKING, Optional, Tuple
import sys

import docker
import docker.errors
from docker.models.containers import Container
from docker.models.images import Image

from .DockerClientFactory import DockerClientFactory
from .DockerRegistryClient import DockerRegistryClient
from .ImageMetadata import ImageMetadata

if TYPE_CHECKING:
    pass

__all__ = ["DockerTemplate"]

TOKEN_URL = "https://auth.docker.io/token"
REGISTRY_URL = "https://registry-1.docker.io"

logger = getLogger(__name__)


def get_line(record):
    if "progress" in record:
        return "{}: {} {}".format(record["id"], record["status"], record["progress"])
    else:
        return "{}: {}".format(record["id"], record["status"])


def print_status(output):
    layers = []
    progress = []

    n = 0

    for record in output:
        status = record["status"]
        if status.startswith("Pulling from") or status.startswith("Digest:") or status.startswith("Status:"):
            continue
        if "id" in record:
            id = record["id"]
            if id in layers:
                progress[layers.index(id)] = get_line(record)
            else:
                layers.append(id)
                progress.append(get_line(record))

        if n > 0:
            print(f"\033[%dA" % n, end="")
            sys.stdout.flush()

        n = len(progress)

        for line in progress:
            print("\033[K" + line)


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

    def get_container(self, name: str) -> Optional[Container]:
        try:
            return self.docker_client.containers.get(name)
        except docker.errors.NotFound:
            return None

    @staticmethod
    def _normalize_image_name(name: str) -> Tuple[str, str]:
        if ":" in name:
            parts = name.split(":")
            assert len(parts) == 2
            return parts[0], parts[1]
        else:
            return name, "latest"

    def pull_image(self, name: str, print_details=False) -> Image:
        repo, tag = self._normalize_image_name(name)
        if print_details:
            output = self.docker_client.api.pull(repo, tag=tag, stream=True, decode=True)
            print_status(output)
        else:
            self.docker_client.images.pull(repo, tag)
        return self.get_image(name)

    def get_image(self, name) -> Optional[Image]:
        try:
            return self.docker_client.images.get(name)
        except docker.errors.ImageNotFound:
            return None

    def has_registry_image(self, name: str) -> bool:
        repo, tag = self._normalize_image_name(name)
        return self.registry_client.has_manifest(repo, tag)

    def has_local_image(self, name: str) -> bool:
        try:
            self.docker_client.images.get(name)
            return True
        except docker.errors.ImageNotFound:
            return False

    def get_branch_image_name(self, name: str, branch: str) -> str:
        if branch == "master":
            return name
        repo, tag = self._normalize_image_name(name)
        branch = branch.replace("/", "-")
        return f"{repo}:{tag}__{branch}"
