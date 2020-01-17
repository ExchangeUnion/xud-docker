from .base import ArgumentParser


class Command:
    def __init__(self, context):
        self._context = context

        parser = ArgumentParser(prog="update", description="Update the whole environment")
        self._parser = parser

    def match(self, *args):
        return args[0] == "update"

    def execute(self, *args):
        self._parser.parse_args(args)
        self._context.update()
        self._context.start()