from launcher.service import ServiceManager
from .types import Command


class CleanupCommand(Command):
    manager: ServiceManager

    def __init__(self, manager: ServiceManager):
        self.manager = manager

    def configure_parser(self, parser):
        pass

    def run(self, args):
        self.manager.cleanup()
