#!/usr/bin/env python3

import json
import os
import platform
import re
import shlex
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

projectdir = abspath(dirname(dirname(__file__)))
projectgithub = "https://github.com/exchangeunion/xud-docker"
imagesdir = join(projectdir, "images")
supportsdir = join(projectdir, "supports")
labelprefix = "com.exchangeunion.image"
group = "exchangeunion"
travis = "TRAVIS_BRANCH" in os.environ
buildx_installed = os.system("docker buildx version 2>/dev/null | grep -q github.com/docker/buildx") == 0
arch = platform.machine()
docker_registry = "registry-1.docker.io"


class GitInfo:
    def __init__(self, branch, revision, master, history):
        self.branch = branch
        self.revision = revision
        self.master = master
        self.history = history


def get_master_commit_hash():
    try:
        return check_output(shlex.split("git rev-parse master")).decode().splitlines()[0]
    except CalledProcessError:
        # <hash> refs/heads/master
        return check_output(shlex.split("git ls-remote origin master")).decode().split()[0]


def get_branch_history(master):
    cmd = "git log --oneline --pretty=format:%h --abbrev=-1 {}..".format(master[:7])
    return check_output(shlex.split(cmd)).decode().splitlines()


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
        history = get_branch_history(master)
        branch = b
        return GitInfo(b, r, master, history)
    return None


os.chdir(projectdir)
now = datetime.utcnow()
created = now.strftime('%Y-%m-%dT%H:%M:%SZ')
utils_tag_date = now.strftime('%y.%m.%d')
gitinfo = create_git_info()
branch = "local"
os.chdir(imagesdir)


def run_command(cmd, errmsg):
    print("$ " + cmd)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)

    for line in p.stdout:
        print(line.decode(), end="")
    print()

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
                r1 = json.loads(payload["history"][0]["v1Compatibility"])["config"]["Labels"]["com.exchangeunion.image.revision"]
                if r1.endswith("-dirty"):
                    return False
                else:
                    if r1 in self.unmodified_history:
                        return True
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
        if self.git:
            labels.extend([
                "--label {}.branch={}".format(labelprefix, self.git.branch),
                "--label {}.revision={}".format(labelprefix, self.git.revision),
            ])
            if not self.git.revision.endswith("-dirty"):
                if self.name == "utils":
                    source = "{}/blob/{}/images/utils/Dockerfile".format(
                        projectgithub, self.git.revision)
                else:
                    source = "{}/blob/{}/images/{}/{}/Dockerfile".format(
                        projectgithub, self.git.revision, self.name, self.tag)
                labels += [
                    "--label {}.source={}".format(labelprefix, source)
                ]
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

    def build(self, args):
        build_tag = self.get_build_tag()

        if self.existed_in_registry_and_up_to_date(docker_registry):
            print("The image {} is up-to-date. Skip building.".format(build_tag))
            return False

        build_labels = self.get_labels()
        build_args = self.get_build_args(args)
        build_dir = self.get_build_dir()

        if not os.path.exists(build_dir):
            print("ERROR: Missing build directory: " + build_dir, file=sys.stderr)
            exit(1)

        args = [
            " ".join(build_args),
            " ".join(build_labels),
        ]

        self.print_title("Building {}".format(self.name), "{} ({})".format(self.tag, self.arch))

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
                build_tag_without_arch = self.get_build_tag_without_arch()
                run_command("docker tag {} {}".format(build_tag, build_tag_without_arch), "Failed to tag {}".format(build_tag_without_arch))
                return True
            else:
                if buildx_installed:
                    buildx_platform = None
                    if self.arch == "aarch64":
                        buildx_platform = "linux/arm64"
                    if not platform:
                        print("Error: The CPU architecture ({}) is not supported currently".format(self.arch), file=sys.stderr)
                        exit(1)
                    cmd = "docker buildx build --platform {} --progress plain --load -f {} -t {} {} {}".format(
                        buildx_platform, dockerfile, build_tag, " ".join(args), build_dir)
                    run_command(cmd, "Failed to build {}".format(build_tag))
                    return True
                else:
                    print("The docker plugin \"buildx\" is not installed. Skip building.")
        finally:
            for f in shared_files:
                os.remove("{}/{}".format(build_dir, f))

        return False

    def push(self):
        if self.build([]):
            tag = self.get_build_tag()
            run_command("docker push {}".format(tag), "Failed to push {}".format(tag))
            return True

        return False

    def __repr__(self):
        return self.get_build_tag()


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
        for img in self.images.values():
            img.push()
        self.create_and_push_manifest_list()

    def get_manifest_tag(self):
        if self.git.branch == "master":
            return "{}/{}:{}".format(self.group, self.name, self.tag)
        else:
            return "{}/{}:{}__{}".format(self.group, self.name, self.tag, self.git.branch.replace("/", "-"))

    def create_and_push_manifest_list(self):
        if buildx_installed:
            t = self.get_manifest_tag()
            t1 = self.images["x86_64"].get_build_tag()
            t2 = self.images["aarch64"].get_build_tag()
            run_command("docker manifest create {} --amend {} --amend {}".format(t, t1, t2), "Failed to create manifest list {}".format(t))
            run_command("docker manifest push -p {}".format(t), "Failed to push manifest list {}".format(t))

    def set_unmodified_history(self, history):
        for img in self.images.values():
            img.unmodified_history = history

    def __repr__(self):
        return self.get_manifest_tag()

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __lt__(self, other):
        return self.__repr__() < other.__repr__()

    def __hash__(self):
        return hash(self.__repr__())


################################################################################


def get_modified_images_at_commit(nodes, commit):
    lines = check_output(shlex.split("git diff --name-only {}".format(commit))).decode().splitlines()

    def f(x):
        if x.startswith("images/utils"):
            return ImageBundle(group, "utils", utils_tag_date, gitinfo)
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

    modified = set()
    for x in lines:
        r = f(x)
        if x.startswith("images") and r:
            if isinstance(r, list):
                modified.update(r)
            else:
                modified.add(r)
    return sorted(modified)


def get_unmodified_history(img, history, history_modified):
    h = history
    for i, m in enumerate(history_modified):
        if img in m:
            h = history[:i]
            break
    return h


def get_modified_images(nodes):
    modified = get_modified_images_at_commit(nodes, gitinfo.master)
    history_modified = []
    for commit in gitinfo.history:
        history_modified.append(get_modified_images_at_commit(nodes, commit))
    for img in modified:
        img.set_unmodified_history(get_unmodified_history(img, gitinfo.history, history_modified))
    return modified


def print_detected_modified_images(modified):
    print("Detected modified images:")
    for img in modified:
        print("- {}".format(img))


def test(args):
    if args.on_cloud:
        os.chdir(projectdir + "/tools/gcloud")
        cmd = "NETWORK={} MACHINE_TYPE={} DISK_SIZE={} NAME_SUFFIX={} ./test.sh {}".format(
            args.network, args.gcloud_machine_type, args.gcloud_disk_size, args.gcloud_name_suffix,
            args.test_script)
        os.system(cmd)
    else:
        os.chdir(projectdir)
        cmd = "./xud.sh -b {}".format(gitinfo.branch)
        os.system(cmd)


def parse_image_with_tag(image):
    if ":" in image:
        parts = image.split(":")
        return parts[0], parts[1]
    else:
        if image == "utils":
            return "utils", utils_tag_date
        else:
            print("ERROR: Missing tag", file=sys.stderr)
            exit(1)


def main():
    global branch

    parser = ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("-b", "--branch", type=str)
    build_parser.add_argument("images", type=str, nargs="*")

    push_parser = subparsers.add_parser("push")
    push_parser.add_argument("-b", "--branch", type=str)
    push_parser.add_argument("--push-dirty", action="store_true")
    push_parser.add_argument("images", type=str, nargs="*")

    test_parser = subparsers.add_parser("test")
    test_parser.add_argument("network", type=str, choices=["simnet", "testnet", "mainnet"])
    test_parser.add_argument("--on-cloud", action="store_true")
    test_parser.add_argument("--gcloud-machine-type", type=str, default="n1-standard-1")
    test_parser.add_argument("--gcloud-disk-size", type=str, default="10GB")
    test_parser.add_argument("--gcloud-name-suffix", type=str, default="")
    if gitinfo:
        test_parser.add_argument("--test-script", type=str, default="test-branch.sh " + gitinfo.branch)
    else:
        test_parser.add_argument("--test-script", type=str, default="test-branch.sh local")

    args = parser.parse_args()

    nodes = json.load(open("utils/launcher/node/nodes.json"))

    if args.command == "build":
        if not gitinfo:
            if not args.branch:
                print("ERROR: No Git repository detected. Please use \"--branch\" to specify a branch manually.", file=sys.stderr)
                exit(1)
            else:
                branch = args.branch
        if len(args.images) == 0:
            # Auto-detect modified images
            modified = get_modified_images(nodes)
            print_detected_modified_images(modified)
            for image in modified:
                image.build()
        else:
            for image in args.images:
                name, tag = parse_image_with_tag(image)
                ImageBundle(group, name, tag, gitinfo).build()
    elif args.command == "push":
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
            modified = get_modified_images(nodes)
            print_detected_modified_images(modified)
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
