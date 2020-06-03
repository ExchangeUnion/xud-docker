from __future__ import annotations

from typing import TYPE_CHECKING

from .abc import Option

if TYPE_CHECKING:
    from ..config import ParseResult
    from ...utils import ArgumentParser


class BranchOption(Option):
    def parse(self, result: ParseResult) -> None:
        assert result.command_line_args

        args = result.command_line_args

        value = "master"

        opt = "branch"
        if hasattr(args, opt):
            value = getattr(args, opt)

        self.value = value

    def configure(self, parser: ArgumentParser) -> None:
        help = (
            "a valid branch inside GitHub ExchangeUnion/xud-docker repository"
        )
        parser.add_argument("--branch", "-b", type=str, help=help)
