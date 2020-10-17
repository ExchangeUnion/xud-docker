from __future__ import annotations

import http.client
import json
import logging
import platform
import re
import sys
import time
from concurrent.futures import wait
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Dict, Any
from urllib.error import HTTPError
from urllib.request import urlopen, Request

from docker import DockerClient
from docker.errors import ImageNotFound

from launcher.errors import FatalError, NoWaiting
from launcher.utils import yes_or_no

if TYPE_CHECKING:
    from .base import Node
    from launcher.config import Config

logger = logging.getLogger(__name__)


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


class ImageMetadata:
    def __init__(self, digest: str, created: datetime, branch: str, revision: str, name: str):
        self.digest = digest
        self.created = created
        self.branch = branch
        self.revision = revision
        self.name = name


@dataclass
class Action:
    type: str
    details: Any


class Image:
    def __init__(self, repo: str, tag: str, branch: str, client: DockerClient, node: Node):
        self.logger = logger
        self.id = None
        self.repo = repo
        self.tag = tag
        self.branch = branch
        self.client = client
        self.node = node

        self.local_metadata = self.fetch_local_metadata()
        self.cloud_metadata = None
        self.status = None
        self.pull_image = None
        if self.local_metadata:
            self.use_image = self.local_metadata.name
        else:
            self.use_image = self.name

    def __repr__(self):
        return "<Image %s>" % self.name

    @property
    def name(self):
        return "{}:{}".format(self.repo, self.tag)

    @property
    def branch_name(self):
        if self.branch == "master":
            return self.name
        else:
            return self.name + "__" + self.branch.replace("/", "-")

    @property
    def digest(self):
        if not self.local_metadata:
            return None
        return self.local_metadata.digest

    def get_image_metadata(self, name):
        image = self.client.images.get(name)
        digest = image.id
        created = datetime.strptime(image.labels["com.exchangeunion.image.created"], "%Y-%m-%dT%H:%M:%SZ")
        branch = image.labels["com.exchangeunion.image.branch"]
        revision = image.labels["com.exchangeunion.image.revision"]
        return ImageMetadata(digest, created, branch, revision, name)

    def fetch_local_metadata(self):
        if self.branch == "master":
            try:
                return self.get_image_metadata(self.name)
            except ImageNotFound:
                pass
        else:
            try:
                return self.get_image_metadata(self.branch_name)
            except ImageNotFound:
                pass
            try:
                return self.get_image_metadata(self.name)
            except ImageNotFound:
                pass

    def get_token(self, repo):
        r = urlopen(f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{repo}:pull")
        return json.load(r)["token"]

    def safe_urlopen(self, request):
        while True:
            try:
                r = urlopen(request)
                return json.load(r)
            except http.client.IncompleteRead:
                time.sleep(1)

    def get_submanifest(self, token, repo, digest):
        request = Request(f"https://registry-1.docker.io/v2/{repo}/manifests/{digest}")
        request.add_header("Authorization", f"Bearer {token}")
        request.add_header("Accept", "application/vnd.docker.distribution.manifest.v2+json")
        request.add_header("Accept", "application/vnd.docker.distribution.manifest.list.v2+json")
        request.add_header("Accept", "application/vnd.docker.distribution.manifest.v1+json")
        return self.safe_urlopen(request)

    def get_image_blob(self, token, repo, digest):
        request = Request(f"https://registry-1.docker.io/v2/{repo}/blobs/{digest}")
        request.add_header("Authorization", f"Bearer {token}")
        return self.safe_urlopen(request)

    def get_cloud_metadata(self, name: str):
        repo, tag = name.split(":")

        token = self.get_token(repo)
        request = Request(f"https://registry-1.docker.io/v2/{repo}/manifests/{tag}")
        request.add_header("Authorization", f"Bearer {token}")
        request.add_header("Accept", "application/vnd.docker.distribution.manifest.list.v2+json")

        try:
            payload = self.safe_urlopen(request)
        except HTTPError as e:
            if e.code == 404:
                return None
            else:
                raise e

        if payload["schemaVersion"] == 2:
            arch = platform.machine()
            if arch == "x86_64":
                arch = "amd64"
            elif arch == "aarch64":
                arch = "arm64"
            for m in payload["manifests"]:
                if arch == m["platform"]["architecture"]:
                    payload = self.get_submanifest(token, repo, m["digest"])
                    digest = payload["config"]["digest"]
                    payload = self.get_image_blob(token, repo, digest)
                    labels = payload["config"]["Labels"]
                    created = datetime.strptime(labels["com.exchangeunion.image.created"], "%Y-%m-%dT%H:%M:%SZ")
                    branch = labels["com.exchangeunion.image.branch"]
                    revision = labels["com.exchangeunion.image.revision"]
                    return ImageMetadata(digest, created, branch, revision, name)
        elif payload["schemaVersion"] == 1:
            config = json.loads(payload["history"][0]["v1Compatibility"])["config"]
            digest = config["Image"]
            labels = config["Labels"]
            created = datetime.strptime(labels["com.exchangeunion.image.created"], "%Y-%m-%dT%H:%M:%SZ")
            branch = labels["com.exchangeunion.image.branch"]
            revision = labels["com.exchangeunion.image.revision"]
            return ImageMetadata(digest, created, branch, revision, name)
        return None

    def fetch_cloud_metadata(self):
        try:
            if self.branch == "master":
                return self.get_cloud_metadata(self.name)
            else:
                result = self.get_cloud_metadata(self.branch_name)
                if not result:
                    result = self.get_cloud_metadata(self.name)
                return result
        except:
            self.logger.exception("Failed to fetch cloud image metadata")

    def _get_update_status(self) -> str:
        """Get image update status

        :return: image status
        - UP_TO_DATE: The local image is the same as the cloud.
        - LOCAL_OUTDATED: The local image hash is different from the cloud.
        - LOCAL_NEWER: The local image is created after the cloud.
        - LOCAL_MISSING: The cloud image exists but no local image.
        - LOCAL_ONLY: The image only exists locally.
        - UNAVAILABLE: The image is not found locally or remotely.
        - USE_LOCAL
        """
        if self.node.node_config["use_local_image"]:
            self.cloud_metadata = None
            return "USE_LOCAL"

        local = self.local_metadata

        self.cloud_metadata = self.fetch_cloud_metadata()
        cloud = self.cloud_metadata

        if not local and not cloud:
            return "UNAVAILABLE"

        if local and not cloud:
            return "LOCAL_ONLY"

        if not local and cloud:
            return "LOCAL_MISSING"

        if local.digest == cloud.digest:
            return "UP_TO_DATE"
        else:
            return "LOCAL_OUTDATED"

    def get_update_action(self) -> str:
        status = self._get_update_status()

        if status in ["LOCAL_MISSING", "LOCAL_OUTDATED"]:
            self.pull_image = self.cloud_metadata.name
            self.use_image = self.pull_image

        if status == "UNAVAILABLE":
            raise Exception("Image unavailable: " + self.name)
        elif status == "LOCAL_ONLY":
            raise UserWarning("Registry image not found (will use local version): " + self.name)
        elif status == "LOCAL_MISSING":
            action = "PULL"
        elif status == "LOCAL_NEWER":
            raise UserWarning("Your local image version is newer than registry one: " + self.name)
        elif status == "LOCAL_OUTDATED":
            action = "PULL"
        elif status == "UP_TO_DATE":
            action = "NONE"
        elif status == "USE_LOCAL":
            action = "NONE"
        else:
            raise Exception("Unexpected status " + status)

        logger.info("Image %s: status=%s, action=%s", self.name, status, action)
        return action

    def pull(self):
        print("Pulling %s..." % self.pull_image)
        repo, tag = self.pull_image.split(":")
        output = self.client.api.pull(repo, tag=tag, stream=True, decode=True)
        print_status(output)


class ImageManager:
    config: Config
    client: DockerClient

    def __init__(self, config: Config, docker_client: DockerClient):
        self.config = config
        self.client = docker_client

        self.images: Dict[str, Image] = {}

    @property
    def branch(self):
        return self.config.branch

    @property
    def nodes(self):
        return self.config.nodes

    def normalize_name(self, name):
        if "/" in name:
            if ":" in name:
                return name
            else:
                return name + ":latest"
        else:
            if ":" in name:
                return "library/" + name
            else:
                return "library/" + name + ":latest"

    def get_image(self, name: str, node: Node) -> Image:
        """Get Image object by name. The name cloud be like "alpine",
        "alpine:3.12" or "exchangeunion/bitcoind:0.20.0". The same normalized
        name will always get the same Image object.

        The name normalization examples:
        - alpine -> library/apline:latest
        - exchangeunion/bitcoind -> exchangeunion/bitcoind:latest

        :param name: The image name
        :return: A Image object
        """

        name = self.normalize_name(name)
        p = re.compile("^(.+/.+):(.+)$")
        m = p.match(name)
        if m:
            repo = m.group(1)
            tag = m.group(2)
            if name not in self.images:
                self.images[name] = Image(repo, tag, self.branch, self.client, node)
            return self.images[name]
        else:
            raise FatalError("Invalid image name: " + name)

    def check_for_updates(self) -> Dict[Image, str]:
        logger.info("Checking for image updates")

        images = list(self.images.values())

        images = [image for image in images if image.node.mode == "native" and not image.node.disabled]

        executor = self.config.executor

        futs = {executor.submit(img.get_update_action): img for img in images}

        while True:
            done, not_done = wait(futs, 30)
            if len(not_done) > 0:
                names = ", ".join([futs[f].name for f in not_done])
                print("Still waiting for update checking results of image(s): %s" % names)
                reply = yes_or_no("Would you like to keep waiting?")
                if reply == "no":
                    raise NoWaiting
            else:
                break

        result = {}
        for f in done:
            try:
                result[futs[f]] = f.result()
            except UserWarning as e:
                print("WARNING: %s" % e)

        return result
