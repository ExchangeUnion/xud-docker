from __future__ import annotations

import json
import platform
from functools import cached_property
from typing import TYPE_CHECKING, Optional, Any, Tuple
from urllib.error import HTTPError
from urllib.request import urlopen, Request
from datetime import datetime
import logging

from .ImageMetadata import ImageMetadata
from launcher.errors import ParseError, IllegalState

if TYPE_CHECKING:
    from http.client import HTTPResponse

__all__ = ["DockerRegistryClient"]
logger = logging.getLogger(__name__)

MANIFEST_V1_MIME_TYPE = "application/vnd.docker.distribution.manifest.v1+json"
MANIFEST_V2_MIME_TYPE = "application/vnd.docker.distribution.manifest.v2+json"
MANIFEST_LIST_V2_MIME_TYPE = "application/vnd.docker.distribution.manifest.list.v2+json"


class DockerRegistryClient:
    def __init__(self, token_url: str, registry_url: str):
        self.token_url = token_url
        self.registry_url = registry_url
        self._tokens = {}

    def get_token(self, repo: str) -> str:
        if repo in self._tokens:
            return self._tokens[repo]
        r = urlopen("{}?service=registry.docker.io&scope=repository:{}:pull".format(self.token_url, repo))
        token = json.loads(r.read())["token"]
        self._tokens[repo] = token
        return token

    def get_manifest(self, repo: str, tag: str) -> Optional[Tuple[str, Any]]:
        url = f"{self.registry_url}/v2/{repo}/manifests/{tag}"
        request = Request(url)
        request.add_header("Authorization", "Bearer " + self.get_token(repo))
        media_types = [
            MANIFEST_LIST_V2_MIME_TYPE,
            MANIFEST_V2_MIME_TYPE,
            MANIFEST_V1_MIME_TYPE,
        ]
        request.add_header("Accept", ",".join(media_types))
        try:
            r: HTTPResponse = urlopen(request)
            digest = r.info().get("Docker-Content-Digest")
            payload = json.loads(r.read())
            return digest, payload
        except HTTPError as e:
            if e.code == 404:
                return None
            else:
                raise e

    def has_manifest(self, repo: str, tag: str) -> bool:
        url = f"{self.registry_url}/v2/{repo}/manifests/{tag}"
        request = Request(url, method="HEAD")
        request.add_header("Authorization", "Bearer " + self.get_token(repo))
        media_types = [
            MANIFEST_LIST_V2_MIME_TYPE,
            MANIFEST_V2_MIME_TYPE,
            MANIFEST_V1_MIME_TYPE,
        ]
        request.add_header("Accept", ",".join(media_types))
        try:
            urlopen(request)
            return True
        except HTTPError as e:
            if e.code == 404:
                return False
            else:
                raise e


    def get_blob(self, repo: str, digest: str) -> Optional[Tuple[str, Any]]:
        url = f"{self.registry_url}/v2/{repo}/blobs/{digest}"
        request = Request(url)
        request.add_header("Authorization", "Bearer {}".format(self.get_token(repo)))
        try:
            r: HTTPResponse = urlopen(request)
            payload = json.loads(r.read().decode())
            digest = r.info().get("Docker-Content-Digest")
            return digest, payload
        except HTTPError as e:
            if e.code == 404:
                return None
            else:
                raise

    def _handle_manifest_v1(self, repo: str, tag: str, digest: str, payload: Any) -> ImageMetadata:
        raise NotImplementedError

    def _handle_manifest_v2(self, repo: str, tag: str, digest: str, payload: Any) -> ImageMetadata:
        digest = payload["config"]["digest"]
        blob = self.get_blob(repo, digest)
        assert blob
        blob_digest, blob_payload = blob
        labels = blob_payload["config"]["Labels"]
        lb_created = labels["com.exchangeunion.image.created"]
        lb_rev = labels["com.exchangeunion.image.revision"]
        lb_app_rev = labels["com.exchangeunion.application.revision"]

        created_at = datetime.strptime(lb_created, "%Y-%m-%dT%H:%M:%SZ")

        return ImageMetadata(
            repo=repo,
            tag=tag,
            digest=digest,
            revision=lb_rev,
            application_revision=lb_app_rev,
            created_at=created_at,
        )

    def _normalize_platform(self, platform: Any) -> str:
        os = platform["os"]
        arch = platform["architecture"]
        variant = platform.get("variant", None)
        if variant:
            return "{}/{}/{}".format(os, arch, variant)
        else:
            return "{}/{}".format(os, arch)

    @cached_property
    def _current_platform(self) -> str:
        m = platform.machine()
        if m == "x86_64":
            return "linux/amd64"
        elif m == "AMD64":  # Windows
            return "linux/amd64"
        elif m == "aarch64":
            return "linux/arm64"
        else:
            raise IllegalState("Unsupported machine type %s" % m)

    def _handle_manifest_list_v2(self, repo: str, tag: str, digest: str, payload: Any) -> Optional[ImageMetadata]:
        subm_digest = None
        for m in payload["manifests"]:
            if self._current_platform == self._normalize_platform(m["platform"]):
                subm_digest = m["digest"]
        if not subm_digest:
            return None
        # get sub-manifest for current platform
        digest, payload = self.get_manifest(repo, subm_digest)
        assert payload["mediaType"] == MANIFEST_V2_MIME_TYPE
        return self._handle_manifest_v2(repo, tag, digest, payload)

    def get_image_metadata(self, repo: str, tag: str) -> Optional[ImageMetadata]:
        result = self.get_manifest(repo, tag)
        if not result:
            return None
        digest, payload = result
        media_type = payload["mediaType"]
        if media_type == MANIFEST_V1_MIME_TYPE:
            return self._handle_manifest_v1(repo, tag, digest, payload)
        elif media_type == MANIFEST_V2_MIME_TYPE:
            return self._handle_manifest_v2(repo, tag, digest, payload)
        elif media_type == MANIFEST_LIST_V2_MIME_TYPE:
            return self._handle_manifest_list_v2(repo, tag, digest, payload)
        else:
            raise ParseError("Invalid media type: %s" % media_type)
