from typing import Protocol


class Command(Protocol):

    def run(self, args) -> None:
        pass

    def configure_parser(self, parser) -> None:
        pass
