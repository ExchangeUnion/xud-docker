from __future__ import annotations

import logging
import os
import sys
from shutil import copyfile
from subprocess import Popen, PIPE, STDOUT, check_output, CalledProcessError
from typing import TYPE_CHECKING, List, Optional
import re
import importlib
import time
import threading

from .docker import ManifestList
from .src import SourceManager

if TYPE_CHECKING:
    from .toolkit import Platform, Context


class Image:
    def __init__(self, context: Context, name: str):
        self.context = context
        p = re.compile(r"^(.+):(.+)$")
        m = p.match(name)
        if m:
            self.name = m.group(1)
            self.tag = m.group(2)
        else:
            p = re.compile(r"^([a-z0-9\-]+)$")
            m = p.match(name)
            if m:
                self.name = m.group(1)
                self.tag = "latest"
            else:
                raise SyntaxError(name)
        self._logger = logging.getLogger("core.Image(%s:%s)" % (self.name, self.tag))

    @property
    def group(self) -> str:
        return self.context.group

    @property
    def branch(self) -> str:
        return self.context.branch

    @property
    def revision(self) -> Optional[str]:
        return self.context.revision

    @property
    def label_prefix(self) -> str:
        return self.context.label_prefix

    @property
    def image_folder(self) -> str:
        return self.context.project_dir + "/images/" + self.name

    def get_build_tag(self, branch: str, platform: Platform = None) -> str:
        tag = "{}/{}:{}".format(self.group, self.name, self.tag)
        if branch != "master":
            tag += "__" + branch.replace("/", "-")
        if platform:
            tag += "__" + platform.tag_suffix
        return tag

    def get_shared_dir(self):
        return "{}/shared".format(self.name)

    def get_labels(self, unmodified_history, application_revision) -> List[str]:
        image_revision = ""
        image_source = ""
        image_travis = ""

        if self.revision:
            if "HEAD" in unmodified_history and len(unmodified_history) > 1:
                revision = self.revision.replace("-dirty", "")
            else:
                revision = self.revision

            image_revision = revision

            if not revision.endswith("-dirty"):
                source = "{}/blob/{}/images/{}/Dockerfile".format(self.context.project_repo, revision, self.name)
                image_source = source

        if "TRAVIS_BUILD_WEB_URL" in os.environ:
            image_travis = os.environ["TRAVIS_BUILD_WEB_URL"]

        prefix = self.label_prefix

        return [
            f"--label {prefix}.image.revision='{image_revision}'",
            f"--label {prefix}.image.source='{image_source}'",
            f"--label {prefix}.image.travis='{image_travis}'",
            f"--label {prefix}.application.revision='{application_revision}'",
            # TODO remove labels below
            f"--label {prefix}.image.branch='master'",
            f"--label {prefix}.application.branch='master'",
            "--label {}.image.created={}".format(prefix, self.context.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')),
        ]

    def print_title(self, title, badge):
        print("-" * 80)
        a = ":: %s ::" % title
        gap = 10
        if 80 - len(a) - len(badge) - gap < 0:
            badge = badge[:80 - len(a) - gap - 3] + "..."
        print("{}{}{}".format(a, " " * (80 - len(a) - len(badge)), badge))
        print("-" * 80)

    def get_existed_dockerfile(self, file):
        if not os.path.exists(file):
            print("ERROR: Missing dockerfile: {}".format(file), file=sys.stderr)
            exit(1)
        return file

    def get_dockerfile(self, build_dir, platform: Platform, dockerfile):
        f = "{}/{}".format(build_dir, dockerfile)
        if platform.tag_suffix == "x86_64":
            return self.get_existed_dockerfile(f)
        elif platform.tag_suffix == "aarch64":
            f2 = "{}/Dockerfile.aarch64".format(build_dir)
            if os.path.exists(f2):
                return f2
            else:
                return self.get_existed_dockerfile(f)

    @property
    def repo(self) -> Optional[str]:
        # TODO improve name repo association
        repo = None
        if self.name == "xud":
            repo = "ExchangeUnion/xud"
        elif self.name == "arby":
            repo = "ExchangeUnion/market-maker-tools"
        elif self.name == "boltz":
            repo = "BoltzExchange/boltz-lnd"
        elif self.name == "connext":
            repo = "connext/rest-api-client"
        return repo

    def _skip_build(self, platform: Platform, unmodified_history: List[str], source_manager) -> bool:
        prefix = "[_skip_build] ({})".format(platform)
        build_tag = self.get_build_tag(self.branch, None)
        manifest = self.context.docker_template.get_manifest(build_tag, platform)
        self._logger.debug(f"%s manifest=%r", prefix, manifest)
        if not manifest:
            return False

        # image_revision = manifest.image_revision
        # self._logger.debug("%s image_revision=%r", prefix, image_revision)
        # if image_revision.endswith("-dirty"):
        #     return False
        # if image_revision not in unmodified_history:
        #     return False

        application_revision = manifest.application_revision
        assert application_revision, "application revision should not be None"
        upstream_revision = source_manager.get_application_revision(self.tag)
        self._logger.info("Revisions\n%s (DockerHub)\n%s (GitHub)", application_revision, upstream_revision)

        return application_revision == upstream_revision

    def _run_command(self, cmd):
        self._logger.info(cmd)

        stop = threading.Event()

        def f():
            nonlocal stop
            while not stop.is_set():
                if "TRAVIS_BRANCH" in os.environ:
                    print("Still building...")
                    stop.wait(10)
                    continue
                print(".", end="", flush=True)
                stop.wait(1)
            print()
        threading.Thread(target=f).start()
        try:
            output = check_output(cmd, shell=True, stderr=STDOUT)
            self._logger.debug("$ %s\n%s", cmd, output.decode())
            stop.set()
        except CalledProcessError as e:
            stop.set()
            print(e.output.decode(), end="", flush=True)
            raise SystemExit(1)
        except:
            stop.set()
            raise

    def _build(self, args: List[str], build_dir: str, build_tag: str) -> None:
        cmd = "docker build {} {}".format(" ".join(args), build_dir)
        # self.run_command(cmd, "Failed to build {}".format(build_tag))
        self._run_command(cmd)

    def _buildx_build(self, args: List[str], build_dir: str, build_tag: str, platform: Platform) -> None:
        cmd = "docker buildx build --platform {} --progress plain --load {} {}" \
            .format(platform, " ".join(args), build_dir)
        # self.run_command(cmd, "Failed to build {}".format(build_tag))
        self._run_command(cmd)

    def build(self, platform: Platform, no_cache: bool, force: bool) -> bool:
        self._logger.info("Build %s:%s (%s)", self.name, self.tag, platform.tag_suffix)
        print("Build %s:%s (%s)" % (self.name, self.tag, platform.tag_suffix))

        unmodified_history = self.context.get_unmodified_history(self)
        self._logger.debug("Unmodified history:\n%s", "\n".join([f"- {commit}" for commit in unmodified_history]))

        source_manager = self.prepare()

        build_tag = self.get_build_tag(self.branch, platform)

        if not force and self._skip_build(platform, unmodified_history, source_manager):
            print("Image is up-to-date. Skip building.")
            self._logger.info("Skip building")
            return False

        build_labels = self.get_labels(unmodified_history, source_manager.get_application_revision(self.tag))
        build_dir = "."

        if not os.path.exists(build_dir):
            print("ERROR: Missing build directory: " + build_dir, file=sys.stderr)
            exit(1)

        shared_dir = self.get_shared_dir()
        shared_files = []
        if os.path.exists(shared_dir):
            shared_files = os.listdir(shared_dir)
            for f in shared_files:
                copyfile("{}/{}".format(shared_dir, f), "{}/{}".format(build_dir, f))

        dockerfile = self.get_dockerfile(build_dir, platform, source_manager.get_dockerfile(self.tag))

        build_args = [f"--build-arg {key}='{value}'" for key, value in source_manager.get_build_args(self.tag).items()]

        args = [
            f"-f {dockerfile}",
            f"-t {build_tag}",
        ]
        if no_cache:
            args.append("--no-cache")

        args.extend(build_labels)
        args.extend(build_args)

        try:
            if self.context.current_platform == platform:
                self._build(args, build_dir, build_tag)

                build_tag_without_arch = self.get_build_tag(self.branch, None)
                # self.run_command("docker tag {} {}".format(build_tag, build_tag_without_arch),
                #                  "Failed to tag {}".format(build_tag_without_arch))
                cmd = "docker tag {} {}".format(build_tag, build_tag_without_arch)
                check_output(cmd, shell=True, stderr=PIPE)
            else:
                self._buildx_build(args, build_dir, build_tag, platform)
        finally:
            for f in shared_files:
                os.remove("{}/{}".format(build_dir, f))

        return True

    def prepare(self):
        self._logger.info("Prepare")
        try:
            os.chdir(self.context.project_dir)
            m = importlib.import_module(f"images.{self.name}.src")
            # m = importlib.reload(m)
            # print(m, dir(m))
            os.chdir(self.image_folder)
            if hasattr(m, "SourceManager"):
                source_manager = m.SourceManager()
            else:
                assert hasattr(m, "REPO_URL"), "REPO_URL is required in src.py"
                repo_url = m.REPO_URL
                source_manager = SourceManager(repo_url)

            version = self.tag

            source_manager.ensure(version)

            return source_manager
        finally:
            os.chdir(self.image_folder)

    def push(self, platform: Platform, no_cache: bool = False, dirty_push: bool = False, force: bool = False) -> None:
        self.build(platform = platform, no_cache=no_cache, force=force)

        tag = self.get_build_tag(self.branch, platform)
        cmd = "docker push {}".format(tag)
        output = self.run_command(cmd, "Failed to push " + tag)
        last_line = output.splitlines()[-1]
        p = re.compile(r"^(.*): digest: (.*) size: (\d+)$")
        m = p.match(last_line)
        assert m
        assert m.group(1) in tag

        new_manifest = "{}/{}@{}".format(self.group, self.name, m.group(2))

        # append to manifest list
        os.environ["DOCKER_CLI_EXPERIMENTAL"] = "enabled"
        t0 = self.get_build_tag(self.branch, None)
        repo, _ = t0.split(":")
        manifest_list = self.context.docker_template.get_manifest(t0)
        if manifest_list:
            assert isinstance(manifest_list, ManifestList)
            # try to update manifests
            tags = []
            for m in manifest_list.manifests:
                print(m.platform, platform)
                if m.platform != platform:
                    tags.append("{}@{}".format(repo, m.digest))
            tags = " ".join(tags)
            cmd = f"docker manifest create {t0} {new_manifest}"
            if len(tags) > 0:
                cmd += " " + tags
            self.run_command(cmd, "Failed to create manifest list")
            self.run_command(f"docker manifest push -p {t0}", "Failed to push manifest list")
        else:
            self.run_command(f"docker manifest create {t0} {new_manifest}",
                             "Failed to create manifest list")
            self.run_command(f"docker manifest push -p {t0}", "Failed to push manifest list")

    def run_command(self, cmd, errmsg) -> str:
        if self.context.dry_run:
            print("[dry-run] $ " + cmd)
            return ""
        else:
            print("$ " + cmd, flush=True)

        p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)

        output = bytearray()

        for data in p.stdout:
            output.extend(data)
            os.write(sys.stdout.fileno(), data)
            sys.stdout.flush()

        exit_code = p.wait()

        if exit_code != 0:
            print("ERROR: {}, exit_code={}".format(errmsg, exit_code), file=sys.stderr)
            sys.exit(1)

        return output.decode()

    def __repr__(self):
        return "<Image name=%r tag=%r branch=%r>" % (self.name, self.tag, self.branch)
