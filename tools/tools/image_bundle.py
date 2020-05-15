import json
from subprocess import check_output, PIPE, CalledProcessError
import os
import sys

from .context import context
from .image import Image
from .errors import ManifestMissing
from .utils import run_command


class ImageBundle:
    def __init__(self, name: str, tag: str):
        self.name = name
        self.tag = tag
        self.images = {
            "x86_64": Image(name, tag, "x86_64"),
            "aarch64": Image(name, tag, "aarch64"),
        }

    @property
    def repo(self):
        return "{}/{}".format(context.group, self.name)

    @property
    def build_tag_without_arch(self):
        if context.git.branch == "master":
            return "{}:{}".format(self.repo, self.tag)
        else:
            return "{}:{}__{}".format(self.repo, self.tag, context.git.tag_safe_branch)

    def build(self):
        for img in self.images.values():
            img.build([])

    def push(self):
        if not context.push_manifest_list_only:
            for img in self.images.values():
                img.push()
        if not context.push_without_manifest_list:
            self.create_and_push_manifest_list()

    def inspect_single_manifest(self, tag):
        try:
            output = check_output("docker manifest inspect {}".format(tag), shell=True, stderr=PIPE)
            config = json.loads(output.decode())["config"]
            digest = config["digest"]
            return digest
        except CalledProcessError as e:
            if e.stderr.decode().startswith("no such manifest"):
                raise ManifestMissing(tag)
            else:
                raise e

    def inspect_manifest_list(self, tag):
        try:
            output = check_output("docker manifest inspect {}".format(tag), shell=True, stderr=PIPE)
            payload = json.loads(output.decode())
            if "manifests" not in payload:
                print("{} is not a manifest list".format(tag), file=sys.stderr)
                return None
            manifests = payload["manifests"]
            result = {}
            for m in manifests:
                p = m["platform"]
                architecture = p["architecture"]
                digest = m["digest"]
                parts = tag.split(":")
                digest_tag = parts[0] + "@" + digest
                digest = self.inspect_single_manifest(digest_tag)
                if architecture == "arm64":
                    result["aarch64"] = digest
                elif architecture == "amd64":
                    result["x86_64"] = digest
            return result
        except CalledProcessError as e:
            if e.stderr.decode().startswith("no such manifest"):
                return None
            else:
                raise e

    def create_and_push_manifest_list(self):
        os.environ["DOCKER_CLI_EXPERIMENTAL"] = "enabled"

        t = self.build_tag_without_arch

        digests = {}
        tags = {}

        for key, value in self.images.items():
            tag = value.build_tag
            tags[key] = tag
            try:
                digest = self.inspect_single_manifest(tag)
                digests[key] = digest
            except ManifestMissing:
                print("The manifest {} is missing. Abort manifest list {} creation.".format(tag, t))
                return

        manifests = self.inspect_manifest_list(t)
        outdated = False
        if manifests:
            for key in self.images.keys():
                if manifests[key] != digests[key]:
                    outdated = True
                    break
        else:
            outdated = True

        if outdated:
            run_command("docker manifest create {} {}".format(t, " ".join(["--amend " + t for t in tags.values()])), "Failed to create manifest list {}".format(t))
            run_command("docker manifest push -p {}".format(t), "Failed to push manifest list {}".format(t))

    def set_unmodified_history(self, history):
        for img in self.images.values():
            img.unmodified_history = history

    @property
    def image_dir(self):
        if self.name == "utils":
            return "utils"
        else:
            return "{}/{}".format(self.name, self.tag)

    def __repr__(self):
        return self.build_tag_without_arch

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __lt__(self, other):
        return self.__repr__() < other.__repr__()

    def __hash__(self):
        return hash(self.__repr__())

