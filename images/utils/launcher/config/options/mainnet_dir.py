from __future__ import annotations

from typing import TYPE_CHECKING

from .abc import Option

if TYPE_CHECKING:
    from ..config import ParseResult
    from ...utils import ArgumentParser


class MainnetDirOption(Option):
    def parse(self, result: ParseResult) -> None:
        assert result.command_line_args

        args = result.command_line_args

        value = None

        opt = "mainnet_dir"
        if hasattr(args, opt):
            value = getattr(args, opt)

        self.value = value

    def configure(self, parser: ArgumentParser) -> None:
        help = (
            "TODO mainnet-dir option help"
        )
        parser.add_argument("--mainnet-dir", type=str, help=help)
