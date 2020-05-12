#!/usr/bin/env python3

import json
import os
import platform
import re
import sys
from argparse import ArgumentParser
from datetime import datetime
from os.path import dirname, abspath, join
from shutil import copyfile
from subprocess import check_output, Popen, PIPE, STDOUT, CalledProcessError
from urllib.error import HTTPError
from urllib.request import urlopen, Request
import http.client
import time


def check_buildx():
    return os.system("docker buildx version 2>/dev/null | grep -q github.com/docker/buildx") == 0


arch = platform.machine()
projectdir = abspath(dirname(dirname(__file__)))
projectgithub = "https://github.com/exchangeunion/xud-docker"
imagesdir = join(projectdir, "images")
supportsdir = join(projectdir, "supports")
labelprefix = "com.exchangeunion.image"
group = "exchangeunion"
docker_registry = "registry-1.docker.io"
dry_run = False
commit_before_travis = "205bbf4d430d906875a30e4a47872145ee9d06ee"
no_cache = False

travis = "TRAVIS_BRANCH" in os.environ
buildx_installed = check_buildx()
cross_build = False
push_without_manifest_list = False
push_manifest_list_only = False


class GitInfo:
    def __init__(self, branch, revision, master, history):
        self.branch = branch
        self.revision = revision
        self.master = master
        self.history = history


def get_master_commit_hash():
    try:
        return check_output("git rev-parse master", shell=True, stderr=PIPE).decode().splitlines()[0]
    except CalledProcessError:
        # <hash> refs/heads/master
        return check_output("git ls-remote origin master", shell=True, stderr=PIPE).decode().split()[0]


def get_branch_history(master):
    cmd = "git log --oneline --pretty=format:%h --abbrev=-1 {}..".format(master[:7])
    return check_output(cmd, shell=True, stderr=PIPE).decode().splitlines()


def get_commit_message(commit):
    if commit == "HEAD":
        return ""
    cmd = "git show -s --format=%B {}".format(commit)
    return check_output(cmd, shell=True, stderr=PIPE).decode().splitlines()[0]


def create_git_info():
    global branch
    if os.path.exists(".git"):
        b = os.popen("git rev-parse --abbrev-ref HEAD").read().strip()
        if b == "HEAD":
            b = os.environ["TRAVIS_BRANCH"]
        if b == "local":
            print("ERROR: Git branch name (local) is reserved", file=sys.stderr)
            exit(1)
        if "__" in b:
            print("ERROR: Git branch name (%s) contains \"__\"" % b, file=sys.stderr)
            exit(1)
        r = os.popen("git rev-parse HEAD").read().strip()
        if os.system("git diff --quiet") != 0:
            r = r + "-dirty"
        master = get_master_commit_hash()
        branch = b
        if branch == "master":
            history = get_branch_history(commit_before_travis)
        else:
            history = get_branch_history(master)

        output = check_output("git diff --name-only", shell=True)
        output = output.decode().strip()
        if len(output) > 0:
            history.insert(0, "HEAD")

        return GitInfo(b, r, master, history)
    return None


os.chdir(projectdir)
now = datetime.utcnow()
created = now.strftime('%Y-%m-%dT%H:%M:%SZ')
utils_tag_date = now.strftime('%y.%m.%d')
branch = "local"
gitinfo = create_git_info()
os.chdir(imagesdir)


def run_command(cmd, errmsg):
    global dry_run

    if dry_run:
        print("[dry-run] $ " + cmd)
        return
    else:
        print("$ " + cmd)

    p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)

    for line in p.stdout:
        print(line.decode(), end="")
    sys.stdout.flush()

    exit_code = p.wait()

    if exit_code != 0:
        print("ERROR: {}, exit_code={}".format(errmsg, exit_code), file=sys.stderr)
        exit(1)


class Image:
    def __init__(self, group, name, tag, gitinfo, arch):
        self.group = group
        self.name = name
        self.tag = tag
        self.git = gitinfo
        self.arch = arch
        self.unmodified_history = []

    def get_build_tag(self):
        global branch
        if branch == "master":
            return "{}/{}:{}__{}".format(self.group, self.name, self.tag, self.arch)
        else:
            return "{}/{}:{}__{}__{}".format(self.group, self.name, self.tag, branch.replace("/", "-"), self.arch)

    def get_build_tag_without_arch(self):
        global branch
        if branch == "master":
            return "{}/{}:{}".format(self.group, self.name, self.tag)
        else:
            return "{}/{}:{}__{}".format(self.group, self.name, self.tag, branch.replace("/", "-"))

    def get_tag(self):
        global branch
        if branch == "master":
            return "{}__{}".format(self.tag, self.arch)
        else:
            return "{}__{}__{}".format(self.tag, branch.replace("/", "-"), self.arch)

    def get_build_dir(self):
        if self.name == "utils":
            return "utils"
        else:
            return "{}/{}".format(self.name, self.tag)

    def get_shared_dir(self):
        return "{}/shared".format(self.name)

    def get_token(self, name):
        r = urlopen("https://auth.docker.io/token?service=registry.docker.io&scope=repository:{}:pull".format(name))
        return json.loads(r.read().decode())["token"]

    def get_github_tag(self, repo, tag):
        try:
            r = urlopen(f"https://api.github.com/repos/{repo}/tags")
            target = [t for t in json.loads(r.read().decode()) if t["name"] == tag]
            if len(target) == 0:
                return None
            else:
                return target[0]["commit"]["sha"]
        except Exception as e:
            raise RuntimeError(e, "Failed to get GitHub repository {} tag {}".format(repo, tag))

    def get_github_branch_revision(self, repo, branch):
        try:
            r = urlopen(f"https://api.github.com/repos/{repo}/git/refs/heads/{branch}")
            return json.loads(r.read().decode())["object"]["sha"]
        except Exception as e:
            raise RuntimeError(e, "Failed to get GitHub repository {} branch {} revision".format(repo, branch))

    def get_github_revision(self, name, branch):
        if name == "xud":
            repo = "ExchangeUnion/xud"
        else:
            return None

        tag = self.get_github_tag(repo, branch)
        if tag:
            return tag
        else:
            return self.get_github_branch_revision(repo, branch)

    def existed_in_registry_and_up_to_date(self, registry):
        name = "{}/{}".format(self.group, self.name)
        tag = self.get_tag()
        token = self.get_token(name)
        url = "https://{}/v2/{}/manifests/{}".format(registry, name, tag)
        request = Request(url)
        request.add_header("Authorization", "Bearer " + token)
        request.add_header("Accept", "application/vnd.docker.distribution.manifest.list.v2+json")
        try:
            while True:
                try:
                    r = urlopen(request)
                    payload = json.loads(r.read().decode())
                    break
                except http.client.IncompleteRead:
                    time.sleep(1)

            if payload["schemaVersion"] == 1:
                labels = json.loads(payload["history"][0]["v1Compatibility"])["config"]["Labels"]
                r1 = labels["com.exchangeunion.image.revision"]
                print("- Registry image revision: {}".format(r1))
                print("- Unmodified history: {}".format(self.unmodified_history))
                if r1.endswith("-dirty"):
                    return False
                else:
                    if r1 in self.unmodified_history:
                        if "com.exchangeunion.application.revision" in labels:
                            r2 = labels["com.exchangeunion.application.revision"]
                            _branch = labels["com.exchangeunion.application.branch"]
                            gr = self.get_github_revision(self.name, _branch)
                            print("- Registry image application: {} ({})".format(r2, _branch))
                            print("- Latest application revision: {}".format(gr))
                            if gr:
                                if r2 == gr:
                                    return True
                                else:
                                    return False
                            else:
                                return True
                        else:
                            return False
                    else:
                        return False
            else:
                print("ERROR: Unexpected schemaVersion: " + payload["schemaVersion"], file=sys.stderr)
                exit(1)
        except HTTPError as e:
            if e.code == 404:
                return False
            else:
                raise e
        except:
            raise

    def get_labels(self):
        labels = [
            "--label {}.created={}".format(labelprefix, created),
        ]
        if branch:
            labels.append("--label {}.branch={}".format(labelprefix, branch))
        if self.git:
            labels.append("--label {}.revision={}".format(labelprefix, self.git.revision))
            if not self.git.revision.endswith("-dirty"):
                if self.name == "utils":
                    source = "{}/blob/{}/images/utils/Dockerfile".format(
                        projectgithub, self.git.revision)
                else:
                    source = "{}/blob/{}/images/{}/{}/Dockerfile".format(
                        projectgithub, self.git.revision, self.name, self.tag)
                labels += [
                    "--label {}.source='{}'".format(labelprefix, source)
                ]
        else:
            labels.extend([
                "--label {}.revision=".format(labelprefix),
                "--label {}.source=".format(labelprefix),
            ])
        if "TRAVIS_BUILD_WEB_URL" in os.environ:
            labels.append("--label {}.travis='{}'".format(labelprefix, os.environ["TRAVIS_BUILD_WEB_URL"]))
        return labels

    def get_build_args(self, args):
        result = []
        for arg in args:
            result.append("--build-arg " + arg)
        return result

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
        if self.arch != arch and not cross_build:
            return False

        self.print_title("Building {}".format(self.name), "{} ({})".format(self.tag, self.arch))

        build_tag = self.get_build_tag()

        if self.existed_in_registry_and_up_to_date(docker_registry):
            print("Image is up-to-date. Skip building.")
            return False

        build_labels = self.get_labels()
        build_args = self.get_build_args(args)
        build_dir = self.get_build_dir()

        if not os.path.exists(build_dir):
            print("ERROR: Missing build directory: " + build_dir, file=sys.stderr)
            exit(1)

        args = []
        if no_cache:
            args.append("--no-cache")

        args.extend(build_args)
        args.extend(build_labels)

        shared_dir = self.get_shared_dir()
        shared_files = []
        if os.path.exists(shared_dir):
            shared_files = os.listdir(shared_dir)
            for f in shared_files:
                copyfile("{}/{}".format(shared_dir, f), "{}/{}".format(build_dir, f))

        dockerfile = self.get_dockerfile(build_dir, self.arch)

        try:
            if self.arch == arch:
                cmd = "docker build -f {} -t {} {} {}".format(dockerfile, build_tag, " ".join(args), build_dir)
                run_command(cmd, "Failed to build {}".format(build_tag))

                app_branch, app_revision = self.get_app_branch_revision(build_tag)
                cmd = f"echo FROM {build_tag} | docker build --label com.exchangeunion.application.revision={app_revision} --label com.exchangeunion.application.branch={app_branch} -t {build_tag} -"
                run_command(cmd, "Failed to append application branch and revision labels to the image: {}".format(build_tag))

                build_tag_without_arch = self.get_build_tag_without_arch()
                run_command("docker tag {} {}".format(build_tag, build_tag_without_arch), "Failed to tag {}".format(build_tag_without_arch))
                return True
            else:
                buildx_platform = None
                if self.arch == "aarch64":
                    buildx_platform = "linux/arm64"
                if not platform:
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
            tag = self.get_build_tag()
            run_command("docker push {}".format(tag), "Failed to push {}".format(tag))
            return True

        return False

    def __repr__(self):
        return self.get_build_tag()


class ManifestMissing(Exception):
    def __init__(self, tag):
        super().__init__(tag)


class ImageBundle:
    def __init__(self, group, name, tag, gitinfo):
        self.group = group
        self.name = name
        self.tag = tag
        self.git = gitinfo
        self.images = {
            "x86_64": Image(group, name, tag, gitinfo, "x86_64"),
            "aarch64": Image(group, name, tag, gitinfo, "aarch64"),
        }

    def build(self):
        for img in self.images.values():
            img.build([])

    def push(self):
        if not push_manifest_list_only:
            for img in self.images.values():
                img.push()
        if not push_without_manifest_list:
            self.create_and_push_manifest_list()

    def get_manifest_tag(self):
        if self.git.branch == "master":
            return "{}/{}:{}".format(self.group, self.name, self.tag)
        else:
            return "{}/{}:{}__{}".format(self.group, self.name, self.tag, self.git.branch.replace("/", "-"))

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

    def get_token(self):
        name = "{}/{}".format(self.group, self.name)
        r = urlopen("https://auth.docker.io/token?service=registry.docker.io&scope=repository:{}:pull".format(name))
        return json.loads(r.read().decode())["token"]

    def get_blob(self, token, name, digest):
        request = Request("https://registry-1.docker.io/v2/{}/blobs/{}".format(name, digest))
        request.add_header("Authorization", "Bearer {}".format(token))
        r = urlopen(request)
        payload = json.loads(r.read().decode())
        return payload

    def get_revision(self, token, digest):
        name = "{}/{}".format(self.group, self.name)
        blob = self.get_blob(token, name, digest)
        return blob["config"]["Labels"]["com.exchangeunion.image.revision"]

    def create_and_push_manifest_list(self):
        os.environ["DOCKER_CLI_EXPERIMENTAL"] = "enabled"

        t = self.get_manifest_tag()

        digests = {}
        tags = {}

        token = self.get_token()

        for key, value in self.images.items():
            tag = value.get_build_tag()
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
        return self.get_manifest_tag()

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __lt__(self, other):
        return self.__repr__() < other.__repr__()

    def __hash__(self):
        return hash(self.__repr__())


################################################################################

def get_modified_image(x):
    if x.startswith("images/utils"):
        return ImageBundle(group, "utils", "latest", gitinfo)
    else:
        p = re.compile(r"^images/([^/]*)/([^/]*)/.*$")
        m = p.match(x)
        if m:
            if m.group(2) == "shared":
                all_tags = []
                for tag in os.listdir(m.group(1)):
                    if tag != "shared":
                        all_tags.append(ImageBundle(group, m.group(1), tag, gitinfo))
                return all_tags
            else:
                return ImageBundle(group, m.group(1), m.group(2), gitinfo)
        else:
            return None


def add_diff_lines_to_modified_images(modified, lines):
    for x in lines:
        r = get_modified_image(x)
        if x.startswith("images") and r:
            if isinstance(r, list):
                modified.update(r)
            else:
                modified.add(r)


def get_modified_images_since_commit(commit):
    result = set()
    lines = check_output("git diff --name-only {}".format(commit), shell=True, stderr=PIPE).decode().splitlines()
    add_diff_lines_to_modified_images(result, lines)
    return sorted(result)


def get_modified_images_at_head():
    result = set()
    lines = check_output("git diff --name-only", shell=True, stderr=PIPE).decode().splitlines()
    add_diff_lines_to_modified_images(result, lines)
    lines = check_output("git diff --name-only --cached", shell=True, stderr=PIPE).decode().splitlines()
    add_diff_lines_to_modified_images(result, lines)
    return sorted(result)


def get_modified_images_at_commit(commit):
    if commit == "HEAD":
        return get_modified_images_at_head()

    result = set()
    lines = check_output("git diff-tree --no-commit-id --name-only -r {}".format(commit), shell=True, stderr=PIPE).decode().splitlines()
    add_diff_lines_to_modified_images(result, lines)
    return sorted(result)


def get_unmodified_history(img, history, history_modified):
    h = history
    for i, m in enumerate(history_modified):
        if img in m:
            h = history[:i + 1]
            break
    return h


def get_modified_images():
    if branch == "master":
        modified = get_modified_images_since_commit(commit_before_travis)
    else:
        modified = get_modified_images_since_commit(gitinfo.master)
    history_modified = []
    print("\033[1mBranch {} history:\033[0m".format(branch))
    for commit in gitinfo.history:
        images = get_modified_images_at_commit(commit)
        history_modified.append(images)
        print("\033[33m{}:\033[0m {}".format(commit[:7], get_commit_message(commit)))
        if len(images) == 0:
            print("  (None)")
        else:
            for img in images:
                print("- {}".format(img.image_dir))
    print("\n\033[1mImages' unmodified history:\033[0m")
    for img in modified:
        unmodified_history = get_unmodified_history(img, gitinfo.history, history_modified)
        print("- {}: {}".format(img.image_dir, ", ".join([h[:7] for h in unmodified_history])))
        img.set_unmodified_history(unmodified_history)
    print()
    return modified


def test(args):
    # if args.on_cloud:
    #     os.chdir(projectdir + "/tools/gcloud")
    #     cmd = "NETWORK={} MACHINE_TYPE={} DISK_SIZE={} NAME_SUFFIX={} ./test.sh {}".format(
    #         args.network, args.gcloud_machine_type, args.gcloud_disk_size, args.gcloud_name_suffix,
    #         args.test_script)
    #     os.system(cmd)
    # else:
    #     os.chdir(projectdir)
    #     cmd = "./xud.sh -b {}".format(gitinfo.branch)
    #     os.system(cmd)
    os.chdir(projectdir)
    exit_code = os.system("python3.8 -m pytest -s")
    if exit_code != 0:
        sys.exit(1)


def parse_image_with_tag(image):
    if ":" in image:
        parts = image.split(":")
        return parts[0], parts[1]
    else:
        if image == "utils":
            return "utils", "latest"
        else:
            print("ERROR: Missing tag", file=sys.stderr)
            exit(1)


def filter_deleted_images(images):
    result = []
    for img in images:
        if os.path.exists(img.image_dir):
            result.append(img)
    return result


def print_modified_images(images):
    if len(images) == 0:
        print("No modified images")
        return
    print("\033[1mDetected modified images:\033[0m")
    for img in images:
        print("- {}".format(img.image_dir))
    print()


def main():
    global branch, dry_run, cross_build, push_manifest_list_only, push_without_manifest_list, no_cache

    parser = ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("-b", "--branch", type=str)
    build_parser.add_argument("--dry-run", action="store_true")
    build_parser.add_argument("--cross-build", action="store_true")
    build_parser.add_argument("--no-cache", action="store_true")
    build_parser.add_argument("images", type=str, nargs="*")

    push_parser = subparsers.add_parser("push")
    push_parser.add_argument("-b", "--branch", type=str)
    push_parser.add_argument("--push-dirty", action="store_true")
    push_parser.add_argument("--dry-run", action="store_true")
    push_parser.add_argument("--cross-build", action="store_true")
    push_parser.add_argument("--manifest-list", action="store_true")
    push_parser.add_argument("--no-manifest-list", action="store_true")
    push_parser.add_argument("--no-cache", action="store_true")
    push_parser.add_argument("images", type=str, nargs="*")

    test_parser = subparsers.add_parser("test")
    # test_parser.add_argument("network", type=str, choices=["simnet", "testnet", "mainnet"])
    # test_parser.add_argument("--on-cloud", action="store_true")
    # test_parser.add_argument("--gcloud-machine-type", type=str, default="n1-standard-1")
    # test_parser.add_argument("--gcloud-disk-size", type=str, default="10GB")
    # test_parser.add_argument("--gcloud-name-suffix", type=str, default="")
    # if gitinfo:
    #     test_parser.add_argument("--test-script", type=str, default="test-branch.sh " + gitinfo.branch)
    # else:
    #     test_parser.add_argument("--test-script", type=str, default="test-branch.sh local")

    args = parser.parse_args()
    if hasattr(args, "dry_run") and args.dry_run:
        dry_run = True

    if args.command == "build":
        if args.no_cache:
            no_cache = True
        if args.cross_build:
            cross_build = buildx_installed
        if not gitinfo:
            if not args.branch:
                print("ERROR: No Git repository detected. Please use \"--branch\" to specify a branch manually.", file=sys.stderr)
                exit(1)
            else:
                branch = args.branch
        if len(args.images) == 0:
            # Auto-detect modified images
            modified = filter_deleted_images(get_modified_images())
            print_modified_images(modified)
            for image in modified:
                image.build()
        else:
            for image in args.images:
                name, tag = parse_image_with_tag(image)
                ImageBundle(group, name, tag, gitinfo).build()
    elif args.command == "push":
        if args.no_cache:
            no_cache = True
        if args.cross_build:
            cross_build = True
        if args.manifest_list:
            push_manifest_list_only = True
        if args.no_manifest_list:
            push_without_manifest_list = True
        if not gitinfo:
            if not args.branch:
                print("ERROR: No Git repository detected. Please use \"--branch\" to specify a branch manually.", file=sys.stderr)
                exit(1)
            else:
                branch = args.branch
        if not args.push_dirty and gitinfo.revision.endswith("-dirty"):
            print("ERROR: Abort pushing because there are uncommitted changes in current working stage. You can use option \"--push-dirty\" to forcefully push dirty images to the registry.", file=sys.stderr)
            exit(1)
        if len(args.images) == 0:
            # Auto-detect modified images
            modified = filter_deleted_images(get_modified_images())
            print_modified_images(modified)
            for image in modified:
                image.push()
        else:
            for image in args.images:
                name, tag = parse_image_with_tag(image)
                ImageBundle(group, name, tag, gitinfo).push()
    elif args.command == "test":
        test(args)


if __name__ == "__main__":
    main()
