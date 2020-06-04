from __future__ import annotations

from typing import TYPE_CHECKING

from .abc import Option

if TYPE_CHECKING:
    from ..config import ParseResult
    from ..types import ArgumentParser


class DisableUpdateOption(Option[bool]):
    def parse(self, result: ParseResult) -> None:
        assert result.command_line_args

        args = result.command_line_args

        value = False

        opt = "disable_update"
        if hasattr(args, opt):
            value = getattr(args, opt)

        self.value = value

    def configure(self, parser: ArgumentParser) -> None:
        help = (
            "a switch to turn on/off update checking"
        )
        parser.add_argument("--disable-update", action="store_true", help=help)
