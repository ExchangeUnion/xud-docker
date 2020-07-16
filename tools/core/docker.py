from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional, List, Literal, Union

import json
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import http.client
import time
import logging
from dataclasses import dataclass
import platform


if TYPE_CHECKING:
    from .toolkit import Context
    from http.client import HTTPResponse


SupportedPlatform = Literal["linux/arm64", "linux/amd64", "linux/386", "linux/ppc64le", "linux/s390s", "linux/arm/v7", "linux/arm/v6"]


class Platform:
    os: str
    architecture: str
    variant: Optional[str]

    def __init__(self, os: str, architecture: str, variant: str = None):
        self.os = os
        self.architecture = architecture
        self.variant = variant

    @property
    def tag_suffix(self):
        if self.architecture == "amd64":
            return "x86_64"
        elif self.architecture == "386":
            return "x86"
        elif self.architecture == "arm64":
            return "aarch64"
        else:
            raise RuntimeError("Unsupported architecture: " + self.architecture)

    def __str__(self):
        if self.variant:
            return "{}/{}/{}".format(self.os, self.architecture, self.variant)
        else:
            return "{}/{}".format(self.os, self.architecture)


LINUX_AMD64 = Platform(os="linux", architecture="amd64")
LINUX_ARM64 = Platform(os="linux", architecture="arm64")
LINUX_386 = Platform(os="linux", architecture="386")
LINUX_ARM_V7 = Platform(os="linux", architecture="arm", variant="v7")
LINUX_ARM_V6 = Platform(os="linux", architecture="arm", variant="v6")
LINUX_PPC64LE = Platform(os="linux", architecture="ppc64le")
LINUX_S390S = Platform(os="linux", architecture="s390s")


class Platforms:
    @staticmethod
    def get(name) -> Platform:
        m = {
            "linux/amd64": LINUX_AMD64,
            "linux/arm64": LINUX_ARM64,
            "linux/386": LINUX_386,
            "linux/arm/v7": LINUX_ARM_V7,
            "linux/arm/v6": LINUX_ARM_V6,
            "linux/ppc64le": LINUX_PPC64LE,
            "linux/s390s": LINUX_S390S,
        }
        return m[name]

    @staticmethod
    def get_current() -> Platform:
        m = platform.machine()
        if m == "x86_64":
            return LINUX_AMD64
        elif m == "aarch64":
            return LINUX_ARM64
        else:
            raise RuntimeError("Unsupported machine type: " + m)


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


class Manifest:
    raw_manifest: Dict
    raw_blob: Dict

    def __init__(self, context: Context, raw_manifest: Dict, raw_blob: Dict, platform: Platform, digest: str):
        self.context = context
        self.raw_manifest = raw_manifest
        self.raw_blob = raw_blob
        self.platform = platform
        self.digest = digest

    @property
    def labels(self) -> Dict[str, str]:
        return self.raw_blob["config"]["Labels"]

    @property
    def image_branch(self):
        return None

    @property
    def image_revision(self) -> str:
        key = f"{self.context.label_prefix}.image.revision"
        return self.labels[key]

    @property
    def application_revision(self) -> Optional[str]:
        key = f"{self.context.label_prefix}.application.revision"
        value = self.labels.get(key, None)
        if value == "None":
            value = None
        return value

    @property
    def application_branch(self) -> Optional[str]:
        key = f"{self.context.label_prefix}.application.branch"
        value = self.labels.get(key, None)
        if value == "None":
            value = None
        return value

    def __repr__(self) -> str:
        return "<Manifest digest={}>".format(self.digest)


class ManifestList:
    manifests: List[Manifest]

    def __init__(self, manifests):
        self.manifests = manifests


class DockerTemplateError(Exception):
    pass


class DockerTemplate:
    def __init__(self, context: Context):
        self._logger = logging.getLogger("core.DockerTemplate")
        self.context = context
        self._client = DockerRegistryClient(token_url="https://auth.docker.io/token", registry_url="https://registry-1.docker.io")

    def _parse_platform(self, platform: Dict) -> Platform:
        os = platform["os"]
        architecture = platform["architecture"]
        variant = platform["variant"] if "variant" in platform else None
        if variant:
            name = "{}/{}/{}".format(os, architecture, variant)
        else:
            name = "{}/{}".format(os, architecture)
        return Platforms.get(name)

    def _handle_v1_manifest(self, repo: str, res: Resource, platform: Platform = None) -> Optional[Manifest]:
        raise NotImplementedError

    def _handle_v2_manifest_list(self, repo: str, res: Resource, platform: Platform = None) -> Optional[Union[ManifestList, Manifest]]:
        payload = res.payload
        if platform:
            digest = None
            for m in payload["manifests"]:
                p = self._parse_platform(m["platform"])
                if p == platform:
                    digest = m["digest"]
            if not digest:
                return None

            manifest = self._client.get_manifest(repo, digest)
            payload = manifest.payload
            assert payload
            assert payload["schemaVersion"] == 2
            assert payload["mediaType"] == "application/vnd.docker.distribution.manifest.v2+json"
            return self._handle_v2_manifest(repo, manifest, platform)
        else:
            manifests = []
            for m in payload["manifests"]:
                digest = m["digest"]
                platform = self._parse_platform(m["platform"])
                manifest = self._client.get_manifest(repo, digest)
                payload = manifest.payload
                assert payload
                assert payload["schemaVersion"] == 2
                assert payload["mediaType"] == "application/vnd.docker.distribution.manifest.v2+json"
                manifests.append(self._handle_v2_manifest(repo, manifest, platform))
            return ManifestList(manifests)

    def _handle_v2_manifest(self, repo: str, res: Resource, platform: Platform) -> Manifest:
        payload = res.payload
        digest = payload["config"]["digest"]
        blob = self._client.get_blob(repo, digest)
        assert blob
        return Manifest(self.context, payload, blob.payload, platform, res.digest)

    def get_manifest(self, name: str, platform: Platform = None) -> Optional[Union[Manifest, ManifestList]]:
        try:
            repo, tag = name.split(":")

            manifest = self._client.get_manifest(repo, tag)
            if not manifest:
                return None
            payload = manifest.payload
            schema_version = payload["schemaVersion"]
            if schema_version == 1:
                return self._handle_v1_manifest(repo, manifest, platform)
            assert schema_version == 2, "Invalid schema version: {}".format(schema_version)

            media_type = payload["mediaType"]
            if media_type == "application/vnd.docker.distribution.manifest.list.v2+json":
                return self._handle_v2_manifest_list(repo, manifest, platform)
            elif media_type == "application/vnd.docker.distribution.manifest.v2+json":
                return self._handle_v2_manifest(repo, manifest, platform)
            else:
                raise AssertionError("Invalid media type: {}".format(media_type))
        except Exception as e:
            raise DockerTemplateError("Failed to get manifest {} for platform {}".format(name, platform)) from e
