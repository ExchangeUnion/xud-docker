import logging
import os
from datetime import datetime
from typing import Optional, List
from subprocess import CalledProcessError, check_output
import json

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

    def build(self,
              images: List[str] = None,
              dry_run: bool = False,
              no_cache: bool = False,
              platforms: List[str] = None,
              ) -> None:
        if platforms:
            platforms = [Platforms.get(name) for name in platforms]
        else:
            platforms = [self.current_platform]

        ctx = self._create_context(dry_run, platforms)

        if images:
            for i, name in enumerate(images):
                if i > 0:
                    print()
                for p in platforms:
                    Image(ctx, name).build(platform=p, no_cache=no_cache)

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

            if images:
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
        raise NotImplementedError

    def release(self):
        raise NotImplementedError

    def export(self, network, args=None):
        os.chdir(self.project_dir)
        os.system("tools/build utils")
        os.chdir("tests")
        cmd = f"NETWORK={network} bash run_utils_test.sh dump_nodes"
        if args:
            cmd += " " + " ".join(args)
        output = check_output(cmd, shell=True)
        j = json.loads(output)

        os.chdir(self.project_dir)
        with open("docker-compose.yml", "w") as f:
            f.write("version: \"2\"\n")
            f.write("services:\n")
            for key, value in j.items():
                f.write("  {}:\n".format(key))

                image = value["image"]
                hostname = value["hostname"]
                environment = value["environment"]
                command = value["command"]
                volumes = value["volumes"]
                ports = value["ports"]

                f.write("    image: {}\n".format(image))
                f.write("    hostname: {}\n".format(hostname))
                if len(environment) > 0:
                    f.write("    environment:\n")
                    for item in environment:
                        f.write("      - {}\n".format(item))
                if len(command) > 0:
                    f.write("    command:\n")
                    for item in command:
                        f.write("      {}\n".format(item))
                if len(volumes) > 0:
                    f.write("    volumes:\n")
                    for item in volumes:
                        f.write("      - {}\n".format(item))
                if len(ports) > 0:
                    f.write("    ports:\n")
                    for item in ports:
                        f.write("      - {}\n".format(item))
