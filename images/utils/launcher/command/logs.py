from .base import ArgumentParser


class Command:
    def __init__(self, context):
        self._context = context

        parser = ArgumentParser(prog="logs", description="fetch the logs of a container")
        parser.add_argument("--tail", metavar='N', type=int, help="number of lines to show from the end of the logs")
        parser.add_argument("container")
        self._parser = parser

    def match(self, *args):
        return args[0] == "logs"

    def run(self, *args):
        args = self._parser.parse_args(args)
        container = self._context.get_container(args.container)
        for line in container.logs(tail=args.tail):
            print(line)
