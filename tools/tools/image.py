import sys
import os
from urllib.request import urlopen
import json
from subprocess import check_output, PIPE
import re
from shutil import copyfile

from .context import context
from .errors import FatalError
from .utils import run_command


class Image:
    def __init__(self, name: str, tag: str, arch: str):
        self.name = name
        self.tag = tag
        self.arch = arch
        self.unmodified_history = []

    @property
    def repo(self):
        return "{}/{}".format(context.group, self.name)

    @property
    def build_tag(self):
        if context.git.branch == "master":
            return "{}:{}__{}".format(self.repo, self.tag, self.arch)
        else:
            return "{}:{}__{}__{}".format(self.repo, self.tag, context.git.tag_safe_branch, self.arch)

    @property
    def build_tag_without_arch(self):
        if context.git.branch == "master":
            return "{}:{}".format(self.repo, self.tag)
        else:
            return "{}:{}__{}".format(self.repo, self.tag, context.git.tag_safe_branch)

    @property
    def manifest_tag(self):
        if context.git.branch == "master":
            return "{}__{}".format(self.tag, self.arch)
        else:
            return "{}__{}__{}".format(self.tag, context.git.tag_safe_branch, self.arch)

    @property
    def build_dir(self):
        if self.name == "utils":
            return "utils"
        else:
            return "{}/{}".format(self.name, self.tag)

    @property
    def shared_dir(self):
        return "{}/shared".format(self.name)
    
    def get_upstream_revision(self, branch):
        if self.name == "xud":
            repo = "ExchangeUnion/xud"
            return context.github_client.get_revision(repo, branch)
        # TODO add other images upstream revision fetching logic here
        return None
        
    def upstream_outdated(self, labels):
        revision = None
        prefix = f"{context.label_prefix}.application"
        revision_label = f"{prefix}.revision"
        branch_label = f"{prefix}.branch"
        if revision_label in labels:
            revision = labels[revision_label]

        if not revision:
            # The cloud image has no application revision
            return False
        
        if branch_label not in labels:
            raise FatalError("{} should be present if {} exists".format(branch_label, revision_label))
        
        branch = labels[branch_label]
        upstream_revision = self.get_upstream_revision(branch)

        if context.debug:
            print("- Registry image application: {} ({})".format(revision, branch))
            print("- Upstream application: {} ({})".format(upstream_revision, branch))
        
        if not upstream_revision:
            # Missing upstream application revision
            return False
        
        return revision != upstream_revision

    @property
    def outdated(self):
        repo = self.repo
        tag = self.manifest_tag
        payload = context.registry_client.get_manifest(repo, tag)
        if not payload:
            return True
        schema_version = payload["schemaVersion"]
        if schema_version == 1:
            config = json.loads(payload["history"][0]["v1Compatibility"])["config"]
            labels = config["Labels"]
            revision = labels["{}.image.revision".format(context.label_prefix)]

            if context.debug:
                print("- Registry image revision: {}".format(revision))
                print("- Unmodified history: {}".format(self.unmodified_history))
            
            if revision.endswith("-dirty"):
                # Always update -dirty image on cloud
                return True
            else:
                if revision not in self.unmodified_history:
                    # The could image is built with old files
                    return True
                return self.upstream_outdated(labels)
        else:
            raise FatalError("Unexpected manifest ({}:{}) schema version: {}".format(repo, tag, schema_version))

    @property
    def build_labels(self):
        prefix = "{}.image".format(context.label_prefix)

        labels = [
            "--label {}.created={}".format(prefix, context.timestamp),
        ]

        if context.git.branch:
            labels.append("--label {}.branch={}".format(prefix, context.git.branch))

        if context.git.revision:
            r = context.git.revision
            labels.append("--label {}.revision={}".format(prefix, r))
            if not r.endswith("-dirty"):
                if self.name == "utils":
                    source = "{}/blob/{}/images/utils/Dockerfile".format(
                        context.project_repo, r)
                else:
                    source = "{}/blob/{}/images/{}/{}/Dockerfile".format(
                        context.project_repo, r, self.name, self.tag)
                labels.append("--label {}.source='{}'".format(prefix, source))
        else:
            labels.extend([
                "--label {}.revision=".format(prefix),
                "--label {}.source=".format(prefix),
            ])

        if "TRAVIS_BUILD_WEB_URL" in os.environ:
            labels.append("--label {}.travis='{}'".format(prefix, os.environ["TRAVIS_BUILD_WEB_URL"]))

        return labels

    def get_build_args(self, args):
        result = []
        for arg in args:
            result.append("--build-arg " + arg)
        return result

    def print_title(self, title, badge):
        print()
        print("-" * 80)
        a = ":: %s ::" % title
        gap = 10
        if 80 - len(a) - len(badge) - gap < 0:
            badge = badge[:80 - len(a) - gap - 3] + "..."
        print("{}{}{}".format(a, " " * (80 - len(a) - len(badge)), badge))
        print("-" * 80)

    def get_existed_dockerfile(self, file):
        if not os.path.exists(file):
            raise FatalError("Missing dockerfile: {}".format(file))
        return file

    def get_dockerfile(self, build_dir, arch):
        f = "{}/Dockerfile".format(build_dir)
        if arch == "x86_64":
            return self.get_existed_dockerfile(f)
        elif arch == "aarch64":
            f2 = "{}/Dockerfile.aarch64".format(build_dir)
            if os.path.exists(f2):
                return f2
            else:
                return self.get_existed_dockerfile(f)

    def get_app_branch_revision(self, build_tag):
        branch = None
        ref = None
        revision = None
        if self.name == "xud":
            try:
                output = check_output(f"docker run -i --rm --entrypoint cat {build_tag} /app/.git/HEAD", shell=True, stderr=PIPE)
                output = output.decode().strip()
                p = re.compile("^ref: (refs/heads/(.+))$")
                m = p.match(output)
                if m:
                    ref = m.group(1)
                    branch = m.group(2)
            except Exception:
                pass

            if not ref:
                try:
                    output = check_output(f"docker run -i --rm --entrypoint cat {build_tag} /app/dist/Version.js | grep exports.default", shell=True, stderr=PIPE)
                    # exports.default = '-c46bc2f';
                    output = output.decode().strip()
                    p = re.compile(r"^exports\.default = '-(.+)';")
                    m = p.match(output)
                    if m:
                        revision = m.group(1)
                except Exception as e:
                    raise RuntimeError(e, "Failed to get application branch from {}".format(build_tag))

            if not revision:
                try:
                    output = check_output(f"docker run -i --rm --entrypoint cat {build_tag} /app/.git/{ref}", shell=True, stderr=PIPE)
                    output = output.decode().strip()
                    revision = output
                except Exception as e:
                    raise RuntimeError(e, "Failed to get application revision from {}".format(build_tag))

            if len(revision) == 7:
                r = urlopen(f"https://api.github.com/repos/ExchangeUnion/xud/commits/{revision}")
                j = json.loads(r.read().decode())
                revision = j["sha"]
                # try to get branches which contain the commit using GitHub undocumented API
                r = urlopen(f"https://github.com/ExchangeUnion/xud/branch_commits/{revision}")
                branches = []
                p = re.compile(r"^.*\"branch\".*>([^<]+)<.*$")
                for line in r.read().decode().splitlines():
                    m = p.match(line)
                    if m:
                        branches.append(m.group(1))
                branch = ",".join(branches)

        return branch, revision

    def build(self, args):
        if self.arch != context.arch and not context.cross_build:
            return False

        self.print_title("Building {}".format(self.name), "{} ({})".format(self.tag, self.arch))

        build_tag = self.build_tag

        if not self.outdated:
            print("\nImage is up-to-date. Skip building.\n")
            return False

        build_labels = self.build_labels
        build_args = self.get_build_args(args)
        build_dir = self.build_dir

        if not os.path.exists(build_dir):
            raise FatalError("Missing build directory: {}".format(build_dir))

        args = []
        if context.no_cache:
            args.append("--no-cache")

        args.extend(build_args)
        args.extend(build_labels)

        shared_dir = self.shared_dir
        shared_files = []
        if os.path.exists(shared_dir):
            shared_files = os.listdir(shared_dir)
            for f in shared_files:
                copyfile("{}/{}".format(shared_dir, f), "{}/{}".format(build_dir, f))

        dockerfile = self.get_dockerfile(build_dir, self.arch)

        try:
            if self.arch == context.arch:
                cmd = "docker build -f {} -t {} {} {}".format(dockerfile, build_tag, " ".join(args), build_dir)
                run_command(cmd, "Failed to build {}".format(build_tag))

                app_branch, app_revision = self.get_app_branch_revision(build_tag)
                cmd = f"echo FROM {build_tag} | docker build --label com.exchangeunion.application.revision={app_revision} --label com.exchangeunion.application.branch={app_branch} -t {build_tag} -"
                run_command(cmd, "Failed to append application branch and revision labels to the image: {}".format(build_tag))

                new_tag = self.build_tag_without_arch
                run_command("docker tag {} {}".format(build_tag, new_tag), "Failed to tag {}".format(new_tag))
                return True
            else:
                buildx_platform = None
                if self.arch == "aarch64":
                    buildx_platform = "linux/arm64"
                if not buildx_platform:
                    print("Error: The CPU architecture ({}) is not supported currently".format(self.arch), file=sys.stderr)
                    exit(1)
                cmd = "docker buildx build --platform {} --progress plain --load -f {} -t {} {} {}".format(
                    buildx_platform, dockerfile, build_tag, " ".join(args), build_dir)
                run_command(cmd, "Failed to build {}".format(build_tag))

                app_branch, app_revision = self.get_app_branch_revision(build_tag)
                cmd = f"echo FROM {build_tag} | docker buildx build --label com.exchangeunion.application.revision={app_revision} --label com.exchangeunion.application.branch={app_branch} -t {build_tag} -"
                run_command(cmd, "Failed to append application branch and revision labels to the image: {}".format(build_tag))

                return True
        finally:
            for f in shared_files:
                os.remove("{}/{}".format(build_dir, f))

    def push(self):
        if self.build([]):
            tag = self.build_tag
            run_command("docker push {}".format(tag), "Failed to push {}".format(tag))
            return True
        return False

    def __repr__(self):
        return self.build_tag
