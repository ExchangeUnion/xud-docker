from __future__ import annotations

from typing import TYPE_CHECKING

from .abc import ServiceOption

if TYPE_CHECKING:
    from ..config import ParseResult
    from ...utils import ArgumentParser


class DisabledOption(ServiceOption):

    def parse(self, result: ParseResult) -> None:
        assert result.preset_conf
        assert result.command_line_args

        service = self.service
        name = service.name
        parsed = result.preset_conf[name]
        args = result.command_line_args

        value = False

        if "disabled" in parsed:
            value = int(parsed["disabled"])

        opt = "{}.disabled".format(name)
        if hasattr(args, opt):
            value = int(getattr(args, opt))

        self.value = value

    def configure(self, parser: ArgumentParser) -> None:
        key = f"--{self.service.name}.disabled"
        help = (
            "a switch to enable/disable a service"
        )
        parser.add_argument(key, action="store_true", help=help)
