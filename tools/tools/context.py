__all__ = ["context"]

import os
import platform
from os.path import abspath, dirname, join
from datetime import datetime

from .git import GitInfo
from .docker_registry import RegistryClient
from .github import GithubClient


class Context:
    def __init__(self):
        self.debug = False
        self.arch = platform.machine()
        self.project_dir = abspath(dirname(dirname(dirname(__file__))))
        self.project_repo = "https://github.com/exchangeunion/xud-docker"
        self.images_dir = join(self.project_dir, "images")
        self.label_prefix = "com.exchangeunion"
        self.group = "exchangeunion"
        self.docker_registry = "registry-1.docker.io"
        self.dry_run = False
        self.commit_before_travis = "205bbf4d430d906875a30e4a47872145ee9d06ee"
        self.no_cache = False
        self.travis = "TRAVIS_BRANCH" in os.environ
        self.buildx_installed = self.check_buildx()
        self.cross_build = False
        self.push_without_manifest_list = False
        self.push_manifest_list_only = False
        self.now = datetime.utcnow()
        self.timestamp = self.now.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.utils_tag_date = self.now.strftime("%y.%m.%d")
        self.branch = "local"
        self.git = GitInfo(self.project_dir, self.commit_before_travis)
        self.registry_client = RegistryClient("https://auth.docker.io", self.docker_registry)
        self.github_client = GithubClient()

    def check_buildx(self):
        return os.system("docker buildx version 2>/dev/null | grep -q github.com/docker/buildx") == 0


context = Context()
