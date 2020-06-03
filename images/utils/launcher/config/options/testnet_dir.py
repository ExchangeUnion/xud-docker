from __future__ import annotations

from typing import TYPE_CHECKING

from .abc import Option

if TYPE_CHECKING:
    from ..config import ParseResult
    from ...utils import ArgumentParser


class TestnetDirOption(Option):
    def parse(self, result: ParseResult) -> None:
        assert result.command_line_args

        args = result.command_line_args

        value = None

        opt = "testnet_dir"
        if hasattr(args, opt):
            value = getattr(args, opt)

        self.value = value

    def configure(self, parser: ArgumentParser) -> None:
        help = (
            "TODO testnet-dir option help"
        )
        parser.add_argument("--testnet-dir", type=str, help=help)
