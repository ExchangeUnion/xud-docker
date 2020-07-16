from __future__ import annotations

import logging
import os
import platform
import sys
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List

from .docker import DockerTemplate, Platform, Platforms
from .git import GitTemplate
from .github import GithubTemplate
from .image import Image
from .travis import TravisTemplate

if TYPE_CHECKING:
    from .docker import SupportedPlatform


class Context:
    group: str
    label_prefix: str
    platforms: List[Platform]
    current_platform: Platform
    dry_run: bool
    no_cache: bool
    branch: str
    timestamp: datetime
    project_repo: str
    project_dir: str
    revision: Optional[str]
    docker_template: DockerTemplate
    github_template: GithubTemplate
    travis_template: TravisTemplate

    def __init__(self,
                 group: str,
                 label_prefix: str,
                 platforms: List[Platform],
                 dry_run: bool,
                 timestamp: datetime,
                 project_repo: str,
                 project_dir: str,
                 git_template: GitTemplate,
                 current_platform: Platform
                 ):
        self._logger = logging.getLogger("core.Context")

        self.group = group
        self.label_prefix = label_prefix
        self.platforms = platforms
        self.current_platform = current_platform
        self.dry_run = dry_run
        self.timestamp = timestamp
        self.project_repo = project_repo
        self.project_dir = project_dir

        self.docker_template = DockerTemplate(self)
        self.github_template = GithubTemplate(self)
        self.travis_template = TravisTemplate(self)
        self.git_template = git_template

        git_info = git_template.git_info

        self.history = git_template.history
        self.revision = git_info.revision
        self.branch = git_info.branch

        self._logger.debug("branch %s history: %r", self.branch, self.history)

    def get_unmodified_history(self, image: Image) -> List[str]:
        for i, commit in enumerate(self.history):
            if image.image_folder in self.history[commit]:
                return list(self.history)[:i + 1]
        return list(self.history)


class Toolkit:
    group: str
    label_prefix: str
    platforms: List[Platform]
    current_platform: Platform
    dry_run: bool

    def __init__(self,
                 project_dir: str,
                 platforms: List[SupportedPlatform],
                 group: str = "exchangeunion",
                 label_prefix: str = "com.exchangeunion",
                 project_repo: str = "https://github.com/exchangeunion/xud-docker",
                 ):
        self._logger = logging.getLogger("core.Toolkit")

        self._logger.debug(
            "Initialize with project_dir=%r, platforms=%r, group=%r, label_prefix=%r, project_repo=%r",
            project_dir, platforms, group, label_prefix, project_repo)

        self.project_dir = project_dir
        self.group = group
        self.label_prefix = label_prefix
        self.platforms = [Platforms.get(name) for name in platforms]
        self.project_repo = project_repo
        self.git_template = GitTemplate(self.project_dir)
        self.current_platform = Platforms.get_current()

    def _create_context(self, dry_run: bool, platforms: List[Platform]):
        return Context(
            group=self.group,
            label_prefix=self.label_prefix,
            platforms=platforms,
            dry_run=dry_run,
            timestamp=datetime.now(),
            project_repo=self.project_repo,
            project_dir=self.project_dir,
            git_template=self.git_template,
            current_platform=self.current_platform,
        )

    def build(self,
              images: List[str] = None,
              dry_run: bool = False,
              no_cache: bool = False,
              cross_build: bool = False,
              force: bool = False,
              ) -> None:

        self._logger.debug("Build with images=%r, dry_run=%r, no_cache=%r, cross_build=%r",
                           images, dry_run, no_cache, cross_build)

        if cross_build:
            platforms = self.platforms
        else:
            platforms = [self.current_platform]

        ctx = self._create_context(dry_run, platforms)

        if images:
            for name in images:
                Image(ctx, name).build(no_cache=no_cache, force=force)
        else:
            for image in self.git_template.get_modified_images(ctx):
                image.build(no_cache=no_cache, force=force)

    def push(self,
             images: List[str] = None,
             dry_run: bool = False,
             no_cache: bool = False,
             cross_build: bool = False,
             dirty_push: bool = False,
             force: bool = False,
             ) -> None:

        self._logger.debug("Build with images=%r, dry_run=%r, no_cache=%r, cross_build=%r, dirty_push=%r, force=%r",
                           images, dry_run, no_cache, cross_build, dirty_push, force)

        if cross_build:
            platforms = self.platforms
        else:
            platforms = [self.current_platform]

        ctx = self._create_context(dry_run, platforms)

        if images:
            for name in images:
                Image(ctx, name).push(no_cache=no_cache, force=force)
        else:
            for image in self.git_template.get_modified_images(ctx):
                image.push(no_cache=no_cache)

    def test(self):
        os.chdir(self.project_dir)
        sys.exit(os.system("python3.8 -m pytest -s"))

    def release(self):
        raise NotImplementedError
