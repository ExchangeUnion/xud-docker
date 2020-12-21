from abc import ABC, abstractmethod
import argparse
from launcher.core import Launcher


class Command(ABC):
    launcher: Launcher

    def __init__(self, launcher: Launcher):
        self.launcher = launcher

    @abstractmethod
    def run(self, args: argparse.Namespace) -> None:
        pass

    @abstractmethod
    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        pass
