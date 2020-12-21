import argparse

from .base import Command


class Setup(Command):

    def configure_parser(self, parser: argparse.ArgumentParser):
        self.launcher.configure_parser(parser)

    def run(self, args: argparse.Namespace):
        self.launcher.apply(args)
        self.launcher.setup()
