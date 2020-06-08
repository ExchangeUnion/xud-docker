import logging
from typing import Dict
import platform
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import json
import http.client
import re
import time
from typing import List
import sys

from docker import DockerClient
from docker.errors import ImageNotFound

from ..utils import parallel_execute, get_useful_error_message
from ..errors import FatalError


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

    def __repr__(self):
        digest = self.digest
        created = self.created
        branch = self.branch
        revision = self.revision
        name = self.name
        return f"<ImageMetadata {name=} {digest=} {created=} {branch=} {revision=}>"


class Image:
    def __init__(self, repo: str, tag: str, branch: str, client: DockerClient):
        self.logger = logging.getLogger("launcher.node.Image")
        self.id = None
        self.repo = repo
        self.tag = tag
        self.branch = branch
        self.client = client

        self.local_metadata = self.fetch_local_metadata()
        self.cloud_metadata = None
        self.status = None
        self.pull_image = None
        if self.local_metadata:
            self.use_image = self.local_metadata.name
        else:
            self.use_image = self.name

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

    def get_status(self):
        self.cloud_metadata = self.fetch_cloud_metadata()
        local = self.local_metadata
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
            if local.created > cloud.created:
                return "LOCAL_NEWER"
            else:
                return "LOCAL_OUTDATED"

    @property
    def status_message(self):
        if self.status == "UNAVAILABLE":
            return "unavailable"
        elif self.status == "LOCAL_ONLY":
            return "local"
        elif self.status == "LOCAL_MISSING":
            return "missing"
        elif self.status == "LOCAL_NEWER":
            return "newer"
        elif self.status == "LOCAL_OUTDATED":
            return "outdated"
        elif self.status == "UP_TO_DATE":
            return "up-to-date"

    def check_for_updates(self):
        self.status = self.get_status()
        if self.status in ["LOCAL_MISSING", "LOCAL_OUTDATED"]:
            self.pull_image = self.cloud_metadata.name
            self.use_image = self.pull_image

    def __repr__(self):
        name = self.name
        use = self.use_image
        pull = self.pull_image
        return f"<Image {name=} {use=} {pull=}>"


class ImageManager:
    def __init__(self, config, shell, client):
        self.logger = logging.getLogger("launcher.node.ImageManager")

        self.branch = config.branch
        self.client = client
        self.shell = shell
        self.nodes = config.nodes

        self.images: Dict[str, Image] = {}

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

    def get_image(self, name: str) -> Image:
        """Get Image object by name. The name cloud be like "alpine",
        "alpine:3.11" or "exchangeunion/bitcoind:0.20.0". The same normalized
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
                self.images[name] = Image(repo, tag, self.branch, self.client)
            return self.images[name]
        else:
            raise FatalError("Invalid image name: " + name)

    def check_for_updates(self) -> List[Image]:
        images = list(self.images.values())
        
        def check_for_light_setup(images, name):
            if name in self.nodes:
                if self.nodes[name]['mode'] != 'native':
                    for image in images:
                        if name in image.name:
                            images.remove(image)
            return images
        
        images = check_for_light_setup(images, 'bitcoind')
        images = check_for_light_setup(images, 'litecoind')
        images = check_for_light_setup(images, 'geth')

        def print_failed(failed):
            print("Failed to check for image updates.")
            for image, error in failed:
                print("- {}: {}".format(image.name, get_useful_error_message(error)))

        def try_again():
            answer = self.shell.yes_or_no("Try again?")
            return answer == "yes"

        parallel_execute(images, lambda i: i.check_for_updates(), 30, print_failed, try_again)

        return images

    def update_images(self):
        for image in self.images.values():
            status = image.status
            pull_image = image.pull_image
            if status in ["LOCAL_MISSING", "LOCAL_OUTDATED"]:
                print("Pulling %s..." % pull_image)
                repo, tag = pull_image.split(":")
                output = self.client.api.pull(repo, tag=tag, stream=True, decode=True)
                print_status(output)
