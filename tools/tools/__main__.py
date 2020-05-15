import sys
from argparse import ArgumentParser
from traceback import print_exc

from .cmd import BuildCommand, PushCommand, TestCommand
from .errors import FatalError
from .context import context

parser = ArgumentParser()
subparsers = parser.add_subparsers(dest="command")

build = BuildCommand(subparsers.add_parser("build"))
push = PushCommand(subparsers.add_parser("push"))
test = TestCommand(subparsers.add_parser("test"))

args = parser.parse_args()

try:
    if args.command == "build":
        build.run(args)
    elif args.command == "push":
        push.run(args)
    elif args.command == "test":
        test.run(args)
except FatalError as e:
    print()
    print("ERROR: {}".format(e), file=sys.stderr)
    print()
    print_exc()
    exit(1)
except KeyboardInterrupt:
    print()
