from .base import ArgumentParser


class Command:
    def __init__(self, context):
        self._context = context

        parser = ArgumentParser(prog="up", description="Create and start the whole environment")
        self._parser = parser

    def match(self, *args):
        return args[0] == "up"

    def execute(self, *args):
        self._parser.parse_args(args)
        self._context.update()
        self._context.start()
