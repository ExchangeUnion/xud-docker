#!/usr/bin/env python3

import sys
import os
from os.path import dirname, abspath, join, isdir
from argparse import ArgumentParser
from shutil import copyfile
import json
from subprocess import check_output, Popen, PIPE, STDOUT
import shlex
import re
import platform
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import HTTPError

projectdir = abspath(dirname(dirname(__file__)))
projectgithub = "https://github.com/exchangeunion/xud-docker"
imagesdir = join(projectdir, "images")
supportsdir = join(projectdir, "supports")
labelprefix = "com.exchangeunion.image"
tagprefix = "exchangeunion"
travis = "TRAVIS_BRANCH" in os.environ
buildx_installed = os.system("docker buildx version | grep -q github.com/docker/buildx") == 0
arch = platform.machine()

os.chdir(projectdir)


def get_git_info():
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
        return b, r
    return None, None

now = datetime.utcnow()
created = now.strftime('%Y-%m-%dT%H:%M:%SZ')
utils_tag_date = now.strftime('%y.%m.%d')
branch, revision = get_git_info()

os.chdir(imagesdir)

images = list(filter(isdir, os.listdir(".")))


####################################################################


def print_title(title, badge):
    print("-" * 80)
    a = ":: %s ::" % title
    gap = 10
    if 80 - len(a) - len(badge) - gap < 0:
        badge = badge[:80 - len(a) - gap - 3] + "..."
    print("{}{}{}".format(a, " " * (80 - len(a) - len(badge)), badge))
    print("-" * 80)


def get_labels(image, tag):
    labels = [
        "--label {}.created={}".format(labelprefix, created),
    ]
    if branch:
        labels.extend([
            "--label {}.branch={}".format(labelprefix, branch),
            "--label {}.revision={}".format(labelprefix, revision),
        ])
    if not revision.endswith("-dirty"):
        if image == "utils":
            source = "{}/blob/{}/images/{}/Dockerfile".format(
                projectgithub, revision, image)
        else:
            source = "{}/blob/{}/images/{}/{}/Dockerfile".format(
                projectgithub, revision, image, tag)
        labels += [
            "--label {}.source={}".format(labelprefix, source)
        ]
    return labels


def get_build_args(args):
    result = []
    for arg in args:
        result.append("--build-arg " + arg)
    return result


def get_branch_tag(tag):
    if branch:
        if branch == "master":
            return tag
        else:
            return tag + "__" + branch.replace("/", "-")
    return tag + "__local"


def get_existed_dockerfile(file):
    if not os.path.exists(file):
        print("ERROR: Missing dockerfile: {}".format(file), file=sys.stderr)
        exit(1)
    return file


def get_dockerfile(build_dir, arch):
    f = "{}/Dockerfile".format(build_dir)
    if arch == "x86_64":
        return get_existed_dockerfile(f)
    elif arch == "aarch64":
        f2 = "{}/Dockerfile.aarch64".format(build_dir)
        if os.path.exists(f2):
            return f2
        else:
            return get_existed_dockerfile(f)


def parse_image_with_tag(image):
    if ":" in image:
        parts = image.split(":")
        name = parts[0]
        tag = parts[1]
    else:
        name = image
        tag = utils_tag_date
    return name, tag


def run_command(cmd, errmsg):
    print()
    print("-"*80)
    print(cmd)
    print("-"*80)
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)

    for line in p.stdout:
        print(line.decode(), end="")

    exit_code = p.wait()

    if exit_code != 0:
        print("ERROR: {}, exit_code={}".format(errmsg, exit_code), file=sys.stderr)
        exit(1)


def build(image):
    image, tag = parse_image_with_tag(image)
    args = []

    print_title("Building {}".format(image), tag)

    labels = get_labels(image, tag)
    build_args = get_build_args(args)
    build_tag = "{}/{}:{}".format(tagprefix, image, get_branch_tag(tag))

    if image == "utils":
        build_dir = "utils"
    else:
        build_dir = "{}/{}".format(image, tag)

    if not os.path.exists(build_dir):
        print("ERROR: Missing build directory: " + build_dir, file=sys.stderr)
        exit(1)

    args = [
        " ".join(build_args),
        " ".join(labels),
    ]

    shared_dir = "{}/shared".format(image)
    shared_files = []
    if os.path.exists(shared_dir):
        shared_files = os.listdir(shared_dir)
        for f in shared_files:
            print("Copying shared file: " + f)
            copyfile("{}/{}".format(shared_dir, f), "{}/{}".format(build_dir, f))
        print()

    try:
        build_cmd = "docker build -f {} -t {} {} {}".format(get_dockerfile(build_dir, arch), build_tag + "__" + arch, " ".join(args), build_dir)
        run_command(build_cmd, "Failed to build {} image".format(arch))

        if arch == "x86_64" and buildx_installed:
            build_cmd = "docker buildx build --platform linux/arm64 --progress plain --load -f {} -t {} {} {}".format(get_dockerfile(build_dir, "aarch64"), build_tag + "__aarch64", " ".join(args), build_dir)
            run_command(build_cmd, "Failed to build aarch64 image")
    finally:
        print()
        for f in shared_files:
            print("Removing shared file: " + f)
            os.remove("{}/{}".format(build_dir, f))


def get_token(name):
    r = urlopen(f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{name}:pull")
    return json.load(r)["token"]


def dockerhub_image_existed(image):
    name, tag = parse_image_with_tag(image)
    name = tagprefix + "/" + name
    tag = get_branch_tag(tag) + "__" + arch
    token = get_token(name)
    request = Request(f"https://registry-1.docker.io/v2/{name}/manifests/{tag}")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/vnd.docker.distribution.manifest.list.v2+json")
    try:
        r = urlopen(request)
        payload = json.load(r)
        if payload["schemaVersion"] == 1:
            r1: str = json.loads(payload["history"][0]["v1Compatibility"])["config"]["Labels"]["com.exchangeunion.image.revision"]
            r2: str = revision
            return r1 == r2 and not r1.endswith("-dirty")
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


def push(image):
    if dockerhub_image_existed(image):
        print("{} existed in registry-1.docker.io".format(image))
        return

    build(image)

    image, tag = parse_image_with_tag(image)

    push_tag = "{}/{}:{}".format(tagprefix, image, get_branch_tag(tag))
    arch_tag = push_tag + "__" + arch

    run_command("docker push {}".format(arch_tag), "Failed to push {}".format(arch_tag))

    if arch == "x86_64" and buildx_installed:
        aarch64_tag = push_tag + "__aarch64"
        run_command("docker push {}".format(aarch64_tag), "Failed to push {}".format(aarch64_tag))
        run_command("docker manifest create {} --amend {} --amend {}".format(push_tag, arch_tag, aarch64_tag), "Failed to create manifest")
        run_command("docker manifest push -p {}".format(push_tag), "Failed to push manifest")


def test(args):
    if args.on_cloud:
        os.chdir(projectdir + "/tools/gcloud")
        cmd = "NETWORK={} MACHINE_TYPE={} DISK_SIZE={} NAME_SUFFIX={} ./test.sh {}".format(
            args.network, args.gcloud_machine_type, args.gcloud_disk_size, args.gcloud_name_suffix,
            args.test_script)
        os.system(cmd)
    else:
        os.chdir(projectdir)
        cmd = "./xud.sh -b {}".format(branch)
        os.system(cmd)


def get_modified_images(nodes):
    master = check_output(shlex.split("git ls-remote origin master")).decode().split()[0]
    lines = check_output(shlex.split("git diff --name-only {}".format(master))).decode().splitlines()

    def f(x):
        if x.startswith("images/utils"):
            return "utils"
        else:
            p = re.compile(r"^images/([^/]*)/([^/]*)/.*$")
            m = p.match(x)
            if m:
                if m.group(2) == "shared":
                    all_tags = []
                    for tag in os.listdir(m.group(1)):
                        if tag != "shared":
                            all_tags.append("{}:{}".format(m.group(1), tag))
                    return all_tags
                else:
                    return "{}:{}".format(m.group(1), m.group(2))
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
    modified = sorted(modified)

    print("Detected modified images:")
    for img in modified:
        print("- {}".format(img))
    return modified


def main():
    parser = ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("images", type=str, nargs="*")

    push_parser = subparsers.add_parser("push")
    push_parser.add_argument("images", type=str, nargs="*")

    test_parser = subparsers.add_parser("test")
    test_parser.add_argument("network", type=str, choices=["simnet", "testnet", "mainnet"])
    test_parser.add_argument("--on-cloud", action="store_true")
    test_parser.add_argument("--gcloud-machine-type", type=str, default="n1-standard-1")
    test_parser.add_argument("--gcloud-disk-size", type=str, default="10GB")
    test_parser.add_argument("--gcloud-name-suffix", type=str, default="")
    test_parser.add_argument("--test-script", type=str, default="test-branch.sh " + branch)

    args = parser.parse_args()

    nodes = json.load(open("utils/launcher/node/nodes.json"))

    if args.command == "build":
        if len(args.images) == 0:
            # Auto-detect modified images
            for image in get_modified_images(nodes):
                build(image)
        else:
            for image in args.images:
                build(image)
    elif args.command == "push":
        if len(args.images) == 0:
            # Auto-detect modified images
            for image in get_modified_images(nodes):
                push(image)
        else:
            for image in args.images:
                push(image)

    elif args.command == "test":
        test(args)


if __name__ == "__main__":
    main()
