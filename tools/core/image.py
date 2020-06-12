from __future__ import annotations

import logging
import os
import sys
from shutil import copyfile
from subprocess import Popen, check_output, PIPE, STDOUT
from typing import TYPE_CHECKING, List, Optional
import re

from .application_metadata import get_application_metadata
from .docker import ManifestList

if TYPE_CHECKING:
    from .toolkit import Platform, Context


class Image:
    def __init__(self, context: Context, name: str):
        self._logger = logging.getLogger("core.Image(%s)" % name)
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
        if self.name == "utils":
            return "utils"
        else:
            return "{}/{}".format(self.name, self.tag)

    def get_build_tag(self, branch: str, platform: Platform = None) -> str:
        tag = "{}/{}:{}".format(self.group, self.name, self.tag)
        if branch != "master":
            tag += "__" + branch.replace("/", "-")
        if platform:
            tag += "__" + platform.tag_suffix
        return tag

    def get_build_dir(self):
        if self.name == "utils":
            return "utils"
        else:
            return "{}/{}".format(self.name, self.tag)

    def get_shared_dir(self):
        return "{}/shared".format(self.name)

    def get_labels(self, unmodified_history):
        label_prefix = self.label_prefix
        labels = [
            "--label {}.image.created={}".format(label_prefix, self.context.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')),
            "--label {}.image.branch={}".format(label_prefix, self.branch)
        ]
        if self.revision:
            if "HEAD" in unmodified_history and len(unmodified_history) > 1:
                revision = self.revision.replace("-dirty", "")
            else:
                revision = self.revision
            labels.append("--label {}.image.revision={}".format(label_prefix, revision))

            if not revision.endswith("-dirty"):
                if self.name == "utils":
                    source = "{}/blob/{}/images/utils/Dockerfile".format(
                        self.context.project_repo, revision)
                else:
                    source = "{}/blob/{}/images/{}/{}/Dockerfile".format(
                        self.context.project_repo, revision, self.name, self.tag)
                labels.append("--label {}.image.source='{}'".format(label_prefix, source))
        else:
            labels.extend([
                "--label {}.revision=".format(label_prefix),
                "--label {}.source=".format(label_prefix),
            ])
        if "TRAVIS_BUILD_WEB_URL" in os.environ:
            labels.append("--label {}.image.travis='{}'".format(label_prefix, os.environ["TRAVIS_BUILD_WEB_URL"]))
        return labels

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

    def get_dockerfile(self, build_dir, platform: Platform):
        f = "{}/Dockerfile".format(build_dir)
        if platform.tag_suffix == "x86_64":
            return self.get_existed_dockerfile(f)
        elif platform.tag_suffix == "aarch64":
            f2 = "{}/Dockerfile.aarch64".format(build_dir)
            if os.path.exists(f2):
                return f2
            else:
                return self.get_existed_dockerfile(f)

    def _skip_build(self, platform: Platform, unmodified_history: List[str]) -> bool:
        prefix = "[_skip_build] ({})".format(platform)
        build_tag = self.get_build_tag(self.branch, None)
        manifest = self.context.docker_template.get_manifest(build_tag, platform)
        self._logger.debug(f"%s manifest=%r", prefix, manifest)
        if not manifest:
            return False

        image_branch = manifest.image_branch
        self._logger.debug("%s image_branch=%r", prefix, image_branch)
        if image_branch != self.context.branch:
            return False

        image_revision = manifest.image_revision
        self._logger.debug("%s image_revision=%r", prefix, image_revision)
        if image_revision.endswith("-dirty"):
            return False
        if image_revision not in unmodified_history:
            return False

        application_revision = manifest.application_revision
        self._logger.debug("%s application_revision=%r", prefix, application_revision)
        if not application_revision:
            return True

        application_branch = manifest.application_branch
        self._logger.debug("%s application_branch=%r", prefix, application_branch)

        upstream_revision = self.context.github_template.get_branch_head_revision(self.name, application_branch)
        self._logger.debug("%s upstream_revision=%r", prefix, upstream_revision)
        if not upstream_revision:
            return True

        return application_revision == upstream_revision

    def _build(self, args: List[str], build_dir: str, build_tag: str) -> None:
        cmd = "docker build {} {}".format(" ".join(args), build_dir)
        self.run_command(cmd, "Failed to build {}".format(build_tag))

        metadata = get_application_metadata(self.name, build_tag, self.context)
        labels = []
        if metadata.revision:
            labels.append(f"--label {self.label_prefix}.application.revision={metadata.revision}")
        if metadata.branch:
            labels.append(f"--label {self.label_prefix}.application.branch={metadata.branch}")
        if len(labels) > 0:
            cmd = "echo FROM {} | docker build {} -t {} -".format(build_tag, " ".join(labels), build_tag)
            errmsg = "Failed to append application branch and revision labels to the image: {}".format(build_tag)
            self.run_command(cmd, errmsg)

    def _buildx_build(self, args: List[str], build_dir: str, build_tag: str, platform: Platform) -> None:
        cmd = "docker buildx build --platform {} --progress plain --load {} {}" \
            .format(platform, " ".join(args), build_dir)
        self.run_command(cmd, "Failed to build {}".format(build_tag))

        metadata = get_application_metadata(self.name, build_tag, self.context)
        labels = []
        if metadata.revision:
            labels.append(f"--label {self.label_prefix}.application.revision={metadata.revision}")
        if metadata.branch:
            labels.append(f"--label {self.label_prefix}.application.branch={metadata.branch}")
        if len(labels) > 0:
            cmd = "echo FROM {} | docker buildx build {} -t {} -".format(build_tag, " ".join(labels), build_tag)
            errmsg = "Failed to append application branch and revision labels to the image: {}".format(build_tag)
            self.run_command(cmd, errmsg)

    def _build_platform(self, platform: Platform, no_cache: bool = False) -> bool:
        prefix = "[_build_platform] ({})".format(platform)
        build_tag = self.get_build_tag(self.branch, platform)

        unmodified_history = self.context.get_unmodified_history(self)
        self._logger.debug("%s unmodified_history=%r", prefix, unmodified_history)

        if self._skip_build(platform, unmodified_history):
            self._logger.debug("%s Skip building", prefix)
            if platform == self.context.current_platform and "TRAVIS_BRANCH" not in os.environ:
                tag = self.get_build_tag(self.branch)
                self.run_command(f"docker pull {tag}", "Failed to pull " + tag)
                self.run_command(f"docker tag {tag} {build_tag}", "Failed to re-tag " + tag)
            return False

        self.print_title("Building {}".format(self.name), "{} ({})".format(self.tag, platform.tag_suffix))

        build_labels = self.get_labels(unmodified_history)
        build_dir = self.get_build_dir()

        if not os.path.exists(build_dir):
            print("ERROR: Missing build directory: " + build_dir, file=sys.stderr)
            exit(1)

        shared_dir = self.get_shared_dir()
        shared_files = []
        if os.path.exists(shared_dir):
            shared_files = os.listdir(shared_dir)
            for f in shared_files:
                copyfile("{}/{}".format(shared_dir, f), "{}/{}".format(build_dir, f))

        dockerfile = self.get_dockerfile(build_dir, platform)

        args = [
            f"-f {dockerfile}",
            f"-t {build_tag}",
        ]
        if no_cache:
            args.append("--no-cache")

        args.extend(build_labels)

        try:
            if self.context.current_platform == platform:
                self._build(args, build_dir, build_tag)

                build_tag_without_arch = self.get_build_tag(self.branch, None)
                self.run_command("docker tag {} {}".format(build_tag, build_tag_without_arch),
                                 "Failed to tag {}".format(build_tag_without_arch))
            else:
                self._buildx_build(args, build_dir, build_tag, platform)
        finally:
            for f in shared_files:
                os.remove("{}/{}".format(build_dir, f))

        return True

    def build(self, no_cache: bool = False) -> [Platform]:
        os.chdir(self.context.project_dir + "/images")
        result = []
        for p in self.context.platforms:
            if self._build_platform(p, no_cache=no_cache):
                result.append(p)
        return result

    def push(self, no_cache: bool = False, dirty_push: bool = False) -> None:
        platforms = self.build(no_cache=no_cache)

        for platform in platforms:
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
