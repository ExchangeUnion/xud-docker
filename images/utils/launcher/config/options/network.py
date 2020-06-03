from __future__ import annotations

from typing import TYPE_CHECKING

from .abc import Option

if TYPE_CHECKING:
    from ..config import ParseResult
    from ...utils import ArgumentParser


class NetworkOption(Option):
    def parse(self, result: ParseResult) -> None:
        assert result.command_line_args

        args = result.command_line_args

        value = None

        opt = "network"
        if hasattr(args, opt):
            value = getattr(args, opt)

        self.value = value

    def configure(self, parser: ArgumentParser) -> None:
        help = (
            "TODO network option help"
        )
        parser.add_argument("--network", "-n", type=str, help=help)
