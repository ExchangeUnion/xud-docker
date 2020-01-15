#!/usr/bin/env python3

import sys
import os
from os.path import dirname, abspath, join, isdir
from argparse import ArgumentParser
from configparser import ConfigParser
from contextlib import contextmanager
from functools import wraps
import re


def parse_versions():
    parser = ConfigParser(inline_comment_prefixes=(';', '#'))
    parser.read("versions.ini")
    return parser


def is_git_dirty():
    return os.system("git diff --quiet") != 0


projectdir = abspath(dirname(dirname(__file__)))
projectgithub = "https://github.com/exchangeunion/xud-docker"
imagesdir = join(projectdir, "images")
supportsdir = join(projectdir, "supports")
labelprefix = "com.exchangeunion.image"
tagprefix = "exchangeunion"

os.chdir(projectdir)

branch = os.popen("git rev-parse --abbrev-ref HEAD").read().strip()
created = os.popen("date -u +'%Y-%m-%dT%H:%M:%SZ'").read().strip()
revision = os.popen("git rev-parse HEAD").read().strip()

if is_git_dirty:
    revision = revision + "-dirty"

os.chdir(imagesdir)

versions = parse_versions()
images = list(filter(isdir, os.listdir(".")))


####################################################################

@contextmanager
def pushd(new_dir):
    prev_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(prev_dir)


def dir(new_dir):
    def inner_function(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            with pushd(supportsdir):
                function(*args, **kwargs)

        return wrapper

    return inner_function


def get_dockerfile(platform):
    if platform == "linux/arm64":
        f = "Dockerfile.aarch64"
        if os.path.exists(f):
            return f
    return "Dockerfile"


@dir(supportsdir)
def build_xud_simnet(platform):
    dockerfile = get_dockerfile(platform)
    if platform:
        cmd = "docker buildx build --platform {} . -t xud-simnet -f {} --progress plain".format(platform, dockerfile)
    else:
        cmd = "docker build . -t xud-simnet"

    print()
    print(cmd)
    print()

    exit_code = os.system(cmd)

    if exit_code != 0:
        print("Failed to build xud-simnet image", file=sys.stderr)
        exit(1)


def build(image, platform):
    print("-" * 80)
    print(":: Building %s ::" % image)
    print("-" * 80)
    labels = [
        "--label {}.branch={}".format(labelprefix, branch),
        "--label {}.created={}".format(labelprefix, created),
        "--label {}.revision={}".format(labelprefix, revision),
    ]
    if not revision.endswith("-dirty"):
        source = "{}/blob/{}/images/{}/Dockerfile".format(
            projectgithub, revision, image)
        labels += [
            "--label {}.source={}".format(labelprefix, source)
        ]
    build_args = {
        "ALPINE_VERSION": versions["base"]["alpine"],
        "GOLANG_VERSION": versions["base"]["golang"],
        "PYTHON_VERSION": versions["base"]["python"],
        "NODE_VERSION": versions["base"]["node"],
    }
    if image.endswith("-simnet"):
        tag = "{}/{}".format(tagprefix, image)
        build_xud_simnet(platform)
    else:
        if image in versions["application"]:
            version = versions["application"][image]
            if ":" in version:
                repo_name, repo_branch = version.split(":")
                build_args["REPO"] = repo_name
                build_args["BRANCH"] = repo_branch
            else:
                build_args["VERSION"] = version

        if image in versions["tag"]:
            tagsuffix = versions["tag"][image]
        else:
            tagsuffix = "latest"

        tag = "{}/{}:{}".format(tagprefix, image, tagsuffix)

    os.chdir(image)
    try:
        dockerfile = get_dockerfile(platform)
        with open(dockerfile) as f:
            p = re.compile(r"^ARG (.+)$", re.MULTILINE)
            used_args = p.findall(f.read())

        build_args = {k: v for k, v in build_args.items() if k in used_args}
        build_args = ["--build-arg %s=%s" % (k, v) for k, v in build_args.items()]

        args = [
            "-t {}".format(tag),
            " ".join(build_args),
            " ".join(labels),
        ]

        if platform:
            build_cmd = "docker buildx build --platform {} --progress plain --load -f {} {} .".format(platform, dockerfile, " ".join(args))
        else:
            build_cmd = "docker build {} .".format(" ".join(args))
        print()
        print(build_cmd)
        print()
        os.system(build_cmd)
        print()
    finally:
        os.chdir("..")


def push(image):
    if image in versions["tag"]:
        tagsuffix = versions["tag"][image]
    else:
        tagsuffix = "latest"
    tag = "{}/{}:{}".format(tagprefix, image, tagsuffix)
    if branch == "master":
        os.system("docker push {}".format(tag))
    else:
        newtag = tag + "__" + branch.replace('/', '-')
        os.system("docker tag {} {}".format(tag, newtag))
        os.system("docker push {}".format(newtag))


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


def main():
    parser = ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--platform", type=str)
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

    if args.command == "build":
        if len(args.images) == 0:
            x = images
        else:
            x = list(filter(lambda i: i in images, args.images))
        for image in x:
            build(image, args.platform)
    elif args.command == "push":
        if len(args.images) == 0:
            x = images
        else:
            x = list(filter(lambda i: i in images, args.images))
        for image in x:
            push(image)
    elif args.command == "test":
        test(args)


if __name__ == "__main__":
    main()
