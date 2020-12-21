import logging
import os
import sys
from datetime import datetime
from typing import Optional, List
from subprocess import CalledProcessError, check_output
import re

from .docker import DockerTemplate, Platform, Platforms
from .git import GitTemplate
from .github import GithubTemplate
from .image import Image
from .travis import TravisTemplate


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

        self._logger.debug("Current branch is \"%s\"\n%s", self.branch, self._display_history(self.history))

    def _display_history(self, history):
        lines = []
        for commit, images in history.items():
            lines.append("- {}: {}".format(commit, images))
        return "\n".join(lines)


class Toolkit:
    group: str
    label_prefix: str
    platforms: List[Platform]
    current_platform: Platform
    dry_run: bool

    def __init__(self,
                 project_dir: str,
                 platforms: List[str],
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

    def _get_current_branch(self) -> str:
        cmd = "git branch --show-current"
        print("\033[34m$ %s\033[0m" % cmd, flush=True)
        output = check_output(cmd, shell=True)
        output = output.decode()
        print("%s" % output.rstrip(), flush=True)
        output = output.strip()
        return output

    def _get_modified_images(self) -> List[str]:
        branch = self._get_current_branch()
        if branch == "master":
            cmd = "git diff --name-only HEAD^..HEAD images"
        else:
            cmd = "git diff --name-only $(git merge-base --fork-point origin/master)..HEAD images"
        print("\033[34m$ %s\033[0m" % cmd, flush=True)
        output = check_output(cmd, shell=True)
        output = output.decode()
        print("%s" % output.rstrip(), flush=True)
        lines = output.splitlines()
        p = re.compile(r"^images/(.+?)/.*$")
        images = set()
        for line in lines:
            m = p.match(line)
            assert m, "mismatch line (%r): %s" % (p, line)
            image = m.group(1)
            images.add(image)

        print()
        print("Modified images: " + ", ".join(images))
        print()

        images.remove("utils")

        return list(images)

    def build(self,
              images: List[str] = None,
              dry_run: bool = False,
              no_cache: bool = False,
              platforms: List[str] = None,
              ) -> None:
        try:
            if platforms:
                platforms = [Platforms.get(name) for name in platforms]
            else:
                platforms = [self.current_platform]

            ctx = self._create_context(dry_run, platforms)

            if not images:
                images = self._get_modified_images()

            for i, name in enumerate(images):
                if i > 0:
                    print()
                for p in platforms:
                    Image(ctx, name).build(platform=p, no_cache=no_cache)

        except Exception as e:
            p = e
            while p:
                if isinstance(p, CalledProcessError):
                    print("$ %s" % p.cmd)
                    print(p.output.decode().strip())
                    break
                p = e.__cause__
            raise

    def push(self,
             images: List[str] = None,
             dry_run: bool = False,
             no_cache: bool = False,
             platforms: List[str] = None,
             dirty_push: bool = False,
             ) -> None:
        try:
            if platforms:
                platforms = [Platforms.get(name) for name in platforms]
            else:
                platforms = [self.current_platform]

            ctx = self._create_context(dry_run, platforms)

            if not images:
                images = self._get_modified_images()

            for i, name in enumerate(images):
                if i > 0:
                    print()
                for p in platforms:
                    Image(ctx, name).push(platform=p, no_cache=no_cache, dirty_push=dirty_push)

        except Exception as e:
            p = e
            while p:
                if isinstance(p, CalledProcessError):
                    print("$ %s" % p.cmd)
                    print(p.output.decode().strip())
                    break
                p = e.__cause__
            raise

    def test(self):
        os.chdir(self.project_dir)
        sys.exit(os.system("python3.8 -m pytest -s"))

    def release(self):
        raise NotImplementedError
