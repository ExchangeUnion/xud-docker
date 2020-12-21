from launcher.service import ServiceManager
from .types import Command


class SetupCommand(Command):
    manager: ServiceManager

    def __init__(self, manager: ServiceManager):
        self.manager = manager

    def configure_parser(self, parser):
        self.manager.configure_parser(parser)

    def run(self, args):
        self.manager.apply()
        self.manager.setup()
