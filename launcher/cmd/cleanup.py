import argparse
from .base import Command


class Cleanup(Command):
    def configure_parser(self, parser: argparse.ArgumentParser):
        parser.add_argument("-y", "--yes", action="store_true")

    def run(self, args: argparse.Namespace):
        self.launcher.cleanup(no_question=args.yes)
