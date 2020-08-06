from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional, List, Literal, Union

import json
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import http.client
import time
from datetime import datetime
from dataclasses import dataclass
import platform
import docker


if TYPE_CHECKING:
    from http.client import HTTPResponse


class DockerRegistryClientError(Exception):
    pass


@dataclass
class Resource:
    digest: str
    payload: Dict


class DockerRegistryClient:
    def __init__(self, token_url, registry_url):
        self.token_url = token_url
        self.registry_url = registry_url

    def get_token(self, repo):
        try:
            r = urlopen("{}?service=registry.docker.io&scope=repository:{}:pull".format(self.token_url, repo))
            return json.loads(r.read().decode())["token"]
        except Exception as e:
            raise DockerRegistryClientError("Failed to get token for repository: {}".format(repo)) from e

    def get_manifest(self, repo: str, tag: str) -> Optional[Resource]:
        try:
            url = f"{self.registry_url}/v2/{repo}/manifests/{tag}"
            request = Request(url)
            request.add_header("Authorization", "Bearer " + self.get_token(repo))
            media_types = [
                "application/vnd.docker.distribution.manifest.list.v2+json",
                "application/vnd.docker.distribution.manifest.v2+json",
                "application/vnd.docker.distribution.manifest.v1+json",
            ]
            request.add_header("Accept", ",".join(media_types))
            for i in range(3):
                try:
                    r: HTTPResponse = urlopen(request)
                    payload = json.loads(r.read().decode())
                    digest = r.info().get("Docker-Content-Digest")
                    return Resource(digest=digest, payload=payload)
                except http.client.IncompleteRead:
                    pass
                except HTTPError as e:
                    if e.code == 404:
                        return None
                    else:
                        raise
                time.sleep(1)
            raise RuntimeError("Retried 3 times")
        except Exception as e:
            raise DockerRegistryClientError("Failed to get manifest: {}:{}".format(repo, tag)) from e

    def get_blob(self, repo: str, digest: str) -> Optional[Resource]:
        try:
            url = f"{self.registry_url}/v2/{repo}/blobs/{digest}"
            request = Request(url)
            request.add_header("Authorization", "Bearer {}".format(self.get_token(repo)))
            try:
                r: HTTPResponse = urlopen(request)
                payload = json.loads(r.read().decode())
                digest = r.info().get("Docker-Content-Digest")
                return Resource(digest=digest, payload=payload)
            except HTTPError as e:
                if e.code == 404:
                    return None
                else:
                    raise
        except Exception as e:
            raise DockerRegistryClientError("Failed to get blob: {}@{}".format(repo, digest)) from e


@dataclass
class ImageMetadata:
    repo: str
    tag: str
    digest: str
    revision: str
    application_revision: str
    created_at: datetime


class DockerTemplateError(Exception):
    pass


class DockerTemplate:
    def __init__(self):
        self.registry_client = DockerRegistryClient(token_url="https://auth.docker.io/token", registry_url="https://registry-1.docker.io")
        self.docker_client = docker.from_env()

    def _normalize_platform(self, platform: Dict) -> str:
        os = platform["os"]
        arch = platform["architecture"]
        if "variant" in platform:
            variant = platform["variant"]
        else:
            variant = None
        if variant:
            return "{}/{}/{}".format(os, arch, variant)
        else:
            return "{}/{}".format(os, arch)

    def _current_platform(self) -> str:
        m = platform.machine()
        if m == "x86_64":
            return "linux/amd64"
        elif m == "AMD64":  # Windows
            return "linux/amd64"
        elif m == "aarch64":
            return "linux/arm64"
        else:
            raise RuntimeError("Unsupported machine type %s" % m)

    def _handle_v1_manifest(self, repo: str, tag: str, res: Resource) -> Optional[ImageMetadata]:
        raise NotImplementedError

    def _handle_v2_manifest_list(self, repo: str, tag: str, res: Resource) -> Optional[ImageMetadata]:
        payload = res.payload
        digest = None
        for m in payload["manifests"]:
            p = self._normalize_platform(m["platform"])
            if p == self._current_platform():
                digest = m["digest"]
        if not digest:
            return None

        manifest = self.registry_client.get_manifest(repo, digest)
        payload = manifest.payload
        assert payload
        assert payload["schemaVersion"] == 2
        assert payload["mediaType"] == "application/vnd.docker.distribution.manifest.v2+json"
        return self._handle_v2_manifest(repo, tag, manifest)

    def _handle_v2_manifest(self, repo: str, tag: str, res: Resource) -> ImageMetadata:
        payload = res.payload
        digest = payload["config"]["digest"]
        blob = self.registry_client.get_blob(repo, digest)
        assert blob

        labels = blob.payload["config"]["Labels"]

        created_at = datetime.strptime(labels["com.exchangeunion.image.created"], "%Y-%m-%dT%H:%M:%SZ")

        return ImageMetadata(
            repo=repo,
            tag=tag,
            digest=res.digest,
            revision=labels["com.exchangeunion.image.revision"],
            application_revision=labels["com.exchangeunion.application.revision"],
            created_at=created_at,
        )

    def get_registry_image_metadata(self, repo: str, tag: str) -> Optional[ImageMetadata]:
        try:
            manifest = self.registry_client.get_manifest(repo, tag)
            if not manifest:
                return None
            payload = manifest.payload
            schema_version = payload["schemaVersion"]
            if schema_version == 1:
                return self._handle_v1_manifest(repo, tag, manifest)
            assert schema_version == 2, "Invalid schema version: {}".format(schema_version)

            media_type = payload["mediaType"]
            if media_type == "application/vnd.docker.distribution.manifest.list.v2+json":
                return self._handle_v2_manifest_list(repo, tag, manifest)
            elif media_type == "application/vnd.docker.distribution.manifest.v2+json":
                return self._handle_v2_manifest(repo, tag, manifest)
            else:
                raise AssertionError("Invalid media type: {}".format(media_type))
        except Exception as e:
            raise DockerTemplateError("Failed to get metadata of image %s:%s".format(repo, tag)) from e

    def get_local_image_metadata(self, repo: str, tag: str) -> Optional[ImageMetadata]:
        name = "{}:{}".format(repo, tag)
        image = self.docker_client.images.get(name)
        digest = image.id
        labels = image.labels
        created_at = datetime.strptime(labels["com.exchangeunion.image.created"], "%Y-%m-%dT%H:%M:%SZ")
        return ImageMetadata(
            repo=repo,
            tag=tag,
            digest=digest,
            revision=labels["com.exchangeunion.image.revision"],
            application_revision=labels["com.exchangeunion.application.revision"],
            created_at=created_at,
        )
