import json
import logging
import platform
import re
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Optional, Any, Dict, List, Callable

import docker
import docker.errors

from .errors import ParseError, UnsupportedArchitecture, ImageAccessDenied
from .models import Image, Layer
from .registry import DockerRegistryClient

__all__ = (
    "DockerUtility"
)

UpdateFunc = Optional[Callable[[str, Optional[str], Optional[float]], str]]


@dataclass
class CanonicalName:
    repo: str
    tag: Optional[str]
    digest: Optional[str]

    def __str__(self):
        if self.tag:
            return f"{self.repo}:{self.tag}"
        else:
            return f"{self.repo}@{self.digest}"


class DatetimeParser:
    def __init__(self):
        self._pattern = re.compile(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})\.(\d+)Z")

    def parse(self, dtstr: str) -> datetime:
        """Parse datetime string like 2020-11-17T18:21:43.998965661Z"""

        m = self._pattern.match(dtstr)
        if not m:
            raise ParseError("invalid datetime: " + dtstr)

        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))
        hour = int(m.group(4))
        minute = int(m.group(5))
        second = int(m.group(6))
        microsecond = int(m.group(7)[:6])
        microsecond = "{:<06d}".format(microsecond)
        microsecond = int(microsecond)
        return datetime(year, month, day, hour, minute, second, microsecond, tzinfo=timezone.utc)


class DockerUtility:
    docker_client: docker.DockerClient
    docker_registry_client: DockerRegistryClient

    def __init__(self):
        self.docker_client = docker.from_env()
        self.docker_registry_client = DockerRegistryClient()
        self._p1 = re.compile(r"([^:]+):(.+)")
        self._p2 = re.compile(r"([^@]+)@(sha256:.+)")
        self._dt_parser = DatetimeParser()
        self._logger = logging.getLogger(__name__ + ".DockerUtility")

    def get_image(self, name: str, local: bool = False) -> Optional[Image]:
        if local:
            return self._get_local_image(name)
        else:
            return self._get_registry_image(name)

    def parse_image_name(self, name: str) -> CanonicalName:
        m = self._p1.match(name)
        if m:
            repo = m.group(1)
            tag = m.group(2)
            digest = None
        else:
            m = self._p2.match(name)
            if m:
                repo = m.group(1)
                tag = None
                digest = m.group(2)
            else:
                repo = name
                tag = "latest"
                digest = None

        if "/" not in repo:
            repo = "library/" + repo

        return CanonicalName(repo, tag, digest)

    def _get_local_image(self, name: str) -> Optional[Image]:
        canonical_name = self.parse_image_name(name)
        try:
            img = self.docker_client.images.get(name)
            return Image(
                repo=canonical_name.repo,
                tag=canonical_name.tag,
                digest=img.id,
                created_at=self._dt_parser.parse(img.attrs["Created"]),
                labels=img.labels or {},
                layers=[Layer(digest=layer, size=-1) for layer in img.attrs["RootFS"]["Layers"]]
            )
        except docker.errors.ImageNotFound:
            return None

    def _get_registry_image(self, name: str) -> Optional[Image]:
        canonical_name = self.parse_image_name(name)
        try:
            resp = self.docker_registry_client.get_manifest(canonical_name.repo,
                                                            canonical_name.tag or canonical_name.digest)
            payload = json.load(resp)

            schema_version = payload["schemaVersion"]

            if schema_version == 1:
                return self._handle_v1_manifest(canonical_name, payload)
            elif schema_version == 2:
                return self._handle_v2_manifest(canonical_name, payload)
            else:
                raise ParseError("invalid schema version: " + schema_version)
        except urllib.error.HTTPError as e:
            if e.code == HTTPStatus.NOT_FOUND:
                return None
            elif e.code == HTTPStatus.UNAUTHORIZED:
                raise ImageAccessDenied(name)
            else:
                raise

    def _handle_v1_manifest(self, name: CanonicalName, payload: Dict[str, Any]) -> Optional[Image]:
        raise NotImplementedError

    def _handle_v2_manifest(self, name: CanonicalName, payload: Dict[str, Any]) -> Optional[Image]:
        media_type = payload["mediaType"]
        if media_type == "application/vnd.docker.distribution.manifest.list.v2+json":
            m = self._select_manifest(payload["manifests"])
            if not m:
                return None
            resp = self.docker_registry_client.get_manifest(name.repo, m["digest"])
            return self._handle_v2_manifest(name, json.load(resp))
        elif media_type == "application/vnd.docker.distribution.manifest.v2+json":
            digest = payload["config"]["digest"]
            resp = self.docker_registry_client.get_blob(name.repo, digest)
            blob = json.load(resp)
            return Image(
                repo=name.repo,
                tag=name.tag,
                digest=digest,
                created_at=self._dt_parser.parse(blob["created"]),
                labels=blob["config"]["Labels"] or {},
                layers=[Layer(digest=layer["digest"], size=layer["size"]) for layer in payload["layers"]]
            )

    def _select_manifest(self, manifests: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        current = self.get_current_platform()
        for m in manifests:
            p = m["platform"]
            os = p["os"]
            arch = p["architecture"]
            p = f"{os}/{arch}"
            if p == current:
                return m
        return None

    @staticmethod
    def get_current_platform() -> str:
        m = platform.machine()
        if m == "x86_64":
            target = "linux/amd64"
        elif m == "aarch64":
            target = "linux/arm64"
        else:
            raise UnsupportedArchitecture(m)
        return target

    def pull_image(self, name: str, update: UpdateFunc = None) -> str:
        """Pull image with in-time updates

        :param name: the pulling image name
        :param update: the update callback function
        :return: pulled image digest
        """
        canonical_name = self.parse_image_name(name)
        assert canonical_name.tag

        digest = None

        for payload in self.docker_client.api.pull(
                canonical_name.repo,
                tag=canonical_name.tag, stream=True, decode=True):

            self._logger.debug("Pulling %s: %s", name, payload)

            status = payload["status"]

            if "id" in payload:
                # handle layer events

                id = payload["id"]
                if status == "Downloading":
                    # {'status': 'Downloading', 'progressDetail': {'current': 79985079, 'total': 82104778},
                    #   'progress': '[================================================>  ]  79.99MB/82.1MB',
                    #   'id': '9f8de6cacc4d'}
                    detail = payload["progressDetail"]
                    if callable(update):
                        update("downloading", id, detail["current"] / detail["total"])
                elif status == "Extracting":
                    # {'status': 'Extracting', 'progressDetail': {'current': 63504384, 'total': 75341762},
                    #   'progress': '[==========================================>        ]   63.5MB/75.34MB',
                    #   'id': 'c843ec64a111'}
                    detail = payload["progressDetail"]
                    if callable(update):
                        update("downloading", id, 1.0)
                        update("extracting", id, detail["current"] / detail["total"])
                elif status == "Pull complete":
                    # {'status': 'Pull complete', 'progressDetail': {}, 'id': 'c843ec64a111'}
                    if callable(update):
                        update("extracting", id, 1.0)
            else:
                # handle general events

                if status.startswith("Digest: "):
                    # {'status': 'Digest: sha256:33e4fa7ea4f719b069be3603d09c49010863a9f7d739a7a5f1bf161c73262f51'}
                    digest = status.replace("Digest: ", "")
                elif status.startswith("Status: Downloaded newer image for"):
                    # {'status': 'Status: Downloaded newer image for connextproject/vector_node:837bafa1'}
                    if callable(update):
                        update("done", None, None)
                elif status.startswith("Status: Image is up to date for"):
                    # {'status': 'Status: Image is up to date for connextproject/vector_node:837bafa1'}
                    if callable(update):
                        update("up-to-date", None, None)

        return digest
