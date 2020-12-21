import argparse

from .base import Command


class Attach(Command):
    def run(self, args: argparse.Namespace) -> None:
        pass

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        pass
