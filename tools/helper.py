#!/usr/bin/env python3

from os import chdir, system, popen, getcwd, listdir
from os.path import dirname, abspath, join, isdir
from configparser import ConfigParser
from argparse import ArgumentParser
from contextlib import contextmanager
from functools import wraps


def parse_versions():
    parser = ConfigParser(inline_comment_prefixes=(';', '#'))
    parser.read("versions.ini")
    return parser


def is_git_dirty():
    system("git diff --quiet") != 0


projectdir = abspath(dirname(dirname(__file__)))
projectgithub = "https://github.com/exchangeunion/xud-docker"
imagesdir = join(projectdir, "images")
supportsdir = join(projectdir, "supports")
labelprefix = "com.exchangeunion.image"
tagprefix = "exchangeunion"

chdir(projectdir)

branch = popen("git rev-parse --abbrev-ref HEAD").read().strip()
created = popen("date -u +'%Y-%m-%dT%H:%M:%SZ'").read().strip()
revision = popen("git rev-parse HEAD").read().strip()

if is_git_dirty:
    revision = revision + "-dirty"

chdir(imagesdir)

versions = parse_versions()
images = list(filter(isdir, listdir(".")))

####################################################################

@contextmanager
def pushd(new_dir):
    prev_dir = getcwd()
    chdir(new_dir)
    try:
        yield
    finally:
        chdir(prev_dir)


def dir(new_dir):
    def inner_function(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            with pushd(supportsdir):
                function(*args, **kwargs)
        return wrapper
    return inner_function


@dir(supportsdir)
def build_xud_simnet():
    system("docker build . -t xud-simnet")


def build(image):
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
    build_args = [
        "--build-arg ALPINE_VERSION={}".format(versions["base"]["alpine"]),
        "--build-arg GOLANG_VERSION={}".format(versions["base"]["golang"]),
        "--build-arg PYTHON_VERSION={}".format(versions["base"]["python"]),
        "--build-arg NODE_VERSION={}".format(versions["base"]["node"]),
    ]
    if image.endswith("-simnet"):
        tag = "{}/{}".format(tagprefix, image)
        build_xud_simnet()
        print(getcwd())
    else:
        if image not in versions["application"]:
            version = "latest"
        else:
            version = versions["application"][image]
        tag = "{}/{}:{}".format(tagprefix, image, version)
        build_args += [
            "--build-arg VERSION={}".format(version)
        ]
    args = [
        "-t {}".format(tag),
        image,
        " ".join(build_args),
        " ".join(labels),
    ]
    print("docker build", " ".join(args))
    system("docker build {}".format(" ".join(args)))


def push(image):
    pass


def test(network, command):
    print("Test", network)


def main():
    parser = ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("images", type=str, nargs="*")

    push_parser = subparsers.add_parser("push")
    push_parser.add_argument("images", type=str, nargs="*")

    test_parser = subparsers.add_parser("test")
    test_parser.add_argument("network", type=str, choices=[
                             "regtest", "simnet", "testnet", "mainnet"])
    test_parser.add_argument("-c", "--command", type=str,
                             nargs="?", dest="test_command")

    args = parser.parse_args()

    if args.command == "build":
        if len(args.images) == 0:
            x = images
        else:
            x = list(filter(lambda i: i in images, args.images))
        for image in x:
            build(image)
    elif args.command == "push":
        if len(args.images) == 0:
            x = images
        else:
            x = list(filter(lambda i: i in images, args.images))
        for image in x:
            push(image)
    elif args.command == "test":
        test(args.network, args.test_command)


if __name__ == "__main__":
    main()
