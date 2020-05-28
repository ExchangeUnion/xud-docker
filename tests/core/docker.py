from docker import DockerClient
from typing import Optional, Any, Dict
from datetime import datetime
from dataclasses import dataclass
import logging
from urllib.request import Request, urlopen
import json

logger = logging.getLogger(__name__)


class DockerClientFactory:
    def __init__(self, base_url: str = "unix:///var/run/docker.sock"):
        self.base_url = base_url
        self._clients = []
        self.shared_client = self.make_client()

    def make_client(self, timeout=None) -> DockerClient:
        client = DockerClient(base_url=self.base_url, timeout=timeout)
        self._clients.append(client)
        return client

    def destroy(self):
        self.shared_client.close()
        for client in self._clients:
            client.close()


class TokenManager:
    def __init__(self, token_url):
        self.token_url = token_url

    def get_token(self, repo: str) -> str:
        url = f"{self.token_url}?service=registry.docker.io&scope=repository:{repo}:pull"
        response = urlopen(url)
        payload = json.load(response)
        return payload["token"]


class DockerRegistryClient:
    def __init__(self, registry_url, token_url):
        self.registry_url = registry_url
        self.token_manager = TokenManager(token_url)

    def get_manifest(self, repo: str, tag: str) -> Optional[Any]:
        url = f"{self.registry_url}/{repo}/manifests/{tag}"
        request = Request(url)
        request.add_header("Authorization", f"Bearer {self.token_manager.get_token(repo)}")
        request.add_header("Accept", ",".join([
            "application/vnd.docker.distribution.manifest.v2+json",
            "application/vnd.docker.distribution.manifest.list.v2+json",
            "application/vnd.docker.distribution.manifest.v1+json",
        ]))
        response = urlopen(request)
        payload = json.load(response)
        return payload

    def get_blob(self, repo: str, digest: str) -> Optional[Any]:
        url = f"{self.registry_url}/{repo}/blobs/{digest}"
        request = Request(url)
        request.add_header("Authorization", f"Bearer {self.token_manager.get_token(repo)}")
        response = urlopen(request)
        payload = json.load(response)
        return payload


@dataclass
class ImageLayer:
    digest: str


@dataclass
class ImageMetadata:
    repo: str
    tag: str
    digest: str
    local: bool
    labels: Dict[str, str]
    layers: [ImageLayer]

    @property
    def created_datetime(self) -> datetime:
        return datetime.strptime(self.labels["com.exchangeunion.image.created"], "%Y-%m-%dT%H:%M:%SZ")

    @property
    def revision(self) -> str:
        return self.labels["com.exchangeunion.image.revision"]

    @property
    def branch(self) -> str:
        return self.labels["com.exchangeunion.image.branch"]


class DockerTemplate:
    def __init__(self, docker_client_factory: DockerClientFactory, docker_registry_client: DockerRegistryClient):
        self._docker_client_factory = docker_client_factory
        self._docker_registry_client = docker_registry_client

    def get_manifest(self, repo: str, tag: str) -> Optional[Any]:
        manifest = self._docker_registry_client.get_manifest(repo, tag)
        if not manifest:
            return None
        schema_version = manifest["schemaVersion"]
        media_type = manifest["mediaType"]
        if schema_version == 2:
            if media_type == "application/vnd.docker.distribution.manifest.list.v2+json":
                # manifest list
                manifests = manifest["manifests"]
                targets = [m for m in manifests if m["platform"]["architecture"] == "amd64"]
                if len(targets) == 1:
                    digest = targets[0]["digest"]
                    return self._docker_registry_client.get_manifest(repo, digest)
            elif media_type == "application/vnd.docker.distribution.manifest.v2+json":
                # manifest
                return manifest
        elif schema_version == 1:
            raise RuntimeError("Docker manifest schema version 1 is not supported")
        return None

    def get_image_metadata(self, repo: str, tag: str, local: bool = False) -> Optional[ImageMetadata]:
        if local:
            client = self._docker_client_factory.shared_client
            try:
                image = client.images.get(f"{repo}:{tag}")
                labels = image.attrs["Config"]["Labels"]
                layers = [ImageLayer(digest=digest) for digest in image.attrs["RootFS"]["Layers"]]
                return ImageMetadata(
                    repo=repo,
                    tag=tag,
                    digest=image.id,
                    labels=labels,
                    layers=layers,
                    local=local,
                )
            except:
                logger.exception("Failed to get local image (%s:%s) metadata", repo, tag)
        else:
            try:
                manifest = self.get_manifest(repo, tag)
                digest = manifest["config"]["digest"]
                layers = [ImageLayer(digest=layer["digest"]) for layer in manifest["layers"]]
                blob = self._docker_registry_client.get_blob(repo, digest)
                labels = blob["config"]["Labels"]
                return ImageMetadata(
                    repo=repo,
                    tag=tag,
                    digest=digest,
                    labels=labels,
                    layers=layers,
                    local=local,
                )
            except:
                logger.exception("Failed to get registry image (%s:%s) metadata", repo, tag)
        return None
