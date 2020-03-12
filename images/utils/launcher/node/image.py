import logging
from typing import Dict, Optional
import platform
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import json
import http.client
import re
import time

from docker import DockerClient
from docker.errors import ImageNotFound

from ..utils import parallel_execute, get_useful_error_message


class ImageMetadata:
    def __init__(self, digest: str, created: datetime, size: int, branch: str, revision: str, tag: str):
        self.digest = digest
        self.created = created
        self.size = size
        self.branch = branch
        self.revision = revision
        self.tag = tag

    def __repr__(self):
        return f"<ImageMetadata {self.digest=} {self.created=} {self.size=} {self.branch=} {self.revision=} {self.tag}>"


class Image:
    def __init__(self, group: str, name: str, tag: str, branch: str, client: DockerClient):
        self.logger = logging.getLogger("launcher.node.Image")
        self.group = group
        self.name = name
        self.tag = tag
        self.branch = branch
        self.client = client

        self.qualified_tag = self.get_qualified_tag()

        self.metadata: Dict[str, Optional[ImageMetadata]]= {
            "local": None,
            "remote": None,
        }

        self.status = None
        self.pull_image = None

    def get_qualified_tag(self):
        if self.branch == "master":
            return "{}/{}:{}".format(self.group, self.name, self.tag)
        else:
            return "{}/{}:{}__{}".format(self.group, self.name, self.tag, self.branch.replace("/", "-"))

    def get_master_tag(self):
        return "{}/{}:{}".format(self.group, self.name, self.tag)

    def fetch_local_image_metadata(self):
        try:
            image = self.client.images.get(self.qualified_tag)
            digest = image.id
            created = datetime.strptime(image.labels["com.exchangeunion.image.created"], "%Y-%m-%dT%H:%M:%SZ")
            branch = image.labels["com.exchangeunion.image.branch"]
            revision = image.labels["com.exchangeunion.image.revision"]
            size = image.attrs["Size"]
            return ImageMetadata(digest, created, size, branch, revision, self.qualified_tag)
        except ImageNotFound:
            return None

    def get_token(self, name):
        r = urlopen(f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{name}:pull")
        return json.load(r)["token"]

    def safe_urlopen(self, request):
        while True:
            try:
                r = urlopen(request)
                return json.load(r)
            except http.client.IncompleteRead:
                time.sleep(1)

    def get_submanifest(self, token, name, digest):
        request = Request(f"https://registry-1.docker.io/v2/{name}/manifests/{digest}")
        request.add_header("Authorization", f"Bearer {token}")
        request.add_header("Accept", "application/vnd.docker.distribution.manifest.v2+json")
        request.add_header("Accept", "application/vnd.docker.distribution.manifest.list.v2+json")
        request.add_header("Accept", "application/vnd.docker.distribution.manifest.v1+json")
        return self.safe_urlopen(request)

    def get_image_blob(self, token, name, digest):
        request = Request(f"https://registry-1.docker.io/v2/{name}/blobs/{digest}")
        request.add_header("Authorization", f"Bearer {token}")
        return self.safe_urlopen(request)

    def fetch_registry_image_metadata(self, name, tag):
        qualified_tag = "{}:{}".format(name, tag)

        token = self.get_token(name)
        request = Request(f"https://registry-1.docker.io/v2/{name}/manifests/{tag}")
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
                    digest = self.get_submanifest(token, name, m["digest"])["config"]["digest"]
                    payload = self.get_image_blob(token, name, digest)
                    labels = payload["config"]["Labels"]
                    created = datetime.strptime(labels["com.exchangeunion.image.created"], "%Y-%m-%dT%H:%M:%SZ")
                    size = 0
                    branch = labels["com.exchangeunion.image.branch"]
                    revision = labels["com.exchangeunion.image.revision"]
                    return ImageMetadata(digest, created, size, branch, revision, qualified_tag)
        elif payload["schemaVersion"] == 1:
            config = json.loads(payload["history"][0]["v1Compatibility"])["config"]
            digest = config["Image"]
            labels = config["Labels"]
            created = datetime.strptime(labels["com.exchangeunion.image.created"], "%Y-%m-%dT%H:%M:%SZ")
            size = 0
            branch = labels["com.exchangeunion.image.branch"]
            revision = labels["com.exchangeunion.image.revision"]
            return ImageMetadata(digest, created, size, branch, revision, qualified_tag)
        return None

    def fetch_metadata(self):
        local = self.fetch_local_image_metadata()
        if self.branch == "master":
            name = "{}/{}".format(self.group, self.name)
            remote = self.fetch_registry_image_metadata(name, self.tag)
        else:
            name = "{}/{}".format(self.group, self.name)
            tag = self.tag + "__" + self.branch.replace("/", "-")
            remote = self.fetch_registry_image_metadata(name, tag)
            if not remote:
                remote = self.fetch_registry_image_metadata(name, self.tag)
        self.metadata["local"] = local
        self.metadata["remote"] = remote

    def get_status(self):
        local = self.metadata["local"]
        remote = self.metadata["remote"]
        if not local and not remote:
            return "not_found"
        if local and not remote:
            return "local"
        if not local and remote:
            return "missing"
        if local.digest == remote.digest:
            return "up-to-date"
        else:
            if local.created > remote.created:
                return "newer"
            else:
                return "outdated"

    def check_for_updates(self):
        self.logger.debug("%s: fetch_metadata", self.qualified_tag)
        self.fetch_metadata()
        self.logger.debug("%s: get_status", self.qualified_tag)
        self.status = self.get_status()
        if self.status in ["missing", "up-to-date", "newer", "outdated"]:
            self.pull_image = self.metadata["remote"].tag
        self.logger.debug("%s: status is %s", self.qualified_tag, self.status)

    def __repr__(self):
        return self.get_qualified_tag()

    def __hash__(self):
        return hash(self.__repr__())

    def __eq__(self, other):
        if isinstance(other, Image):
            return self.__repr__() == other.__repr__()
        else:
            return False


class ImageManager:
    def __init__(self, branch, client, shell):
        self.logger = logging.getLogger("launcher.node.ImageManager")
        self.images = set()
        self.branch = branch
        self.client = client
        self.shell = shell

    def add_image(self, image: str):
        p = re.compile("^(.*)/(.*):(.*)$")
        m = p.match(image)
        if m:
            group = m.group(1)
            name = m.group(2)
            tag = m.group(3)
            self.images.add(Image(group, name, tag, self.branch, self.client))
        else:
            raise Exception("Invalid image: " + image)

    def check_for_updates(self):
        images = list(self.images)

        def print_failed(failed):
            print("Failed to check for image updates.")
            for image, error in failed:
                print("- {}: {}".format(image, get_useful_error_message(error)))

        def try_again():
            answer = self.shell.yes_or_no("Try again?")
            return answer == "yes"

        parallel_execute(images, lambda i: i.check_for_updates(), 30, print_failed, try_again)

        return {x.get_master_tag(): (x.status, x.pull_image) for x in self.images}
