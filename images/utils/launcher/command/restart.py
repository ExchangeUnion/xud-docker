from .base import ArgumentParser


class Command:
    def __init__(self, context):
        self._context = context

        parser = ArgumentParser(prog="restart", description="Restart a container")
        parser.add_argument("container")
        self._parser = parser

    def match(self, *args):
        return args[0] == "restart"

    def execute(self, *args):
        args = self._parser.parse_args(args)
        container = self._context.get_container(args.container)
        container.restart()
