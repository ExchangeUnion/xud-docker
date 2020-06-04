from __future__ import annotations

from typing import TYPE_CHECKING

from .abc import Option

if TYPE_CHECKING:
    from ..config import ParseResult
    from ..types import ArgumentParser


class SimnetDirOption(Option[str]):
    def parse(self, result: ParseResult) -> None:
        assert result.command_line_args

        args = result.command_line_args

        value = None

        opt = "simnet_dir"
        if hasattr(args, opt):
            value = getattr(args, opt)

        self.value = value

    def configure(self, parser: ArgumentParser) -> None:
        help = (
            "TODO simnet-dir option help"
        )
        parser.add_argument("--simnet-dir", type=str, help=help)
