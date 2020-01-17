from .base import ArgumentParser


class Command:
    def __init__(self, context):
        self._context = context

        parser = ArgumentParser(prog="down", description="Stop and destroy the whole environment")
        self._parser = parser

    def match(self, *args):
        return args[0] == "down"

    def run(self, *args):
        self._parser.parse_args(args)
        self._context.stop()
        self._context.destroy()
        # TODO Stopping {name} ... done
        # TODO Removing {name} ... done
        # TODO Removing network {name}
