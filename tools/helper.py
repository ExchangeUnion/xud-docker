from argparse import ArgumentParser
import os
import sys
from core import Toolkit
from subprocess import CalledProcessError


def main():
    parser = ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    build_parser = subparsers.add_parser("build", prog="build")
    build_parser.add_argument("--dry-run", action="store_true")
    build_parser.add_argument("--no-cache", action="store_true")
    build_parser.add_argument("--platform", action="append")
    build_parser.add_argument("images", type=str, nargs="*")

    push_parser = subparsers.add_parser("push")
    push_parser.add_argument("--dirty-push", action="store_true")
    push_parser.add_argument("--dry-run", action="store_true")
    push_parser.add_argument("--no-cache", action="store_true")
    push_parser.add_argument("--platform", action="append")
    push_parser.add_argument("images", type=str, nargs="*")

    subparsers.add_parser("test")

    subparsers.add_parser("release")

    args = parser.parse_args()

    project_dir = os.path.abspath(__file__ + "/../..")
    os.chdir(project_dir)

    toolkit = Toolkit(project_dir, ["linux/amd64", "linux/arm64"])
    sys.path.append(project_dir)
    sys.path.append(".")

    if args.command == "build":
        toolkit.build(args.images, args.dry_run, args.no_cache, args.platform)
    elif args.command == "push":
        toolkit.push(args.images, args.dry_run, args.no_cache, args.platform, args.dirty_push)
    elif args.command == "test":
        toolkit.test()
    elif args.command == "release":
        toolkit.release()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        exit(1)
