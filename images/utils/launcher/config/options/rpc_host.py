from __future__ import annotations

from typing import TYPE_CHECKING

from .abc import ServiceOption

if TYPE_CHECKING:
    from ..config import ParseResult
    from ...utils import ArgumentParser


class RpcHostOption(ServiceOption):
    def parse(self, result: ParseResult) -> None:
        assert result.preset_conf
        assert result.command_line_args

        service = self.service
        name = service.name
        parsed = result.preset_conf[name]
        args = result.command_line_args

        value = None

        if "rpc-host" in parsed:
            value = parsed["rpc-host"]

        opt = "{}.rpc_host".format(name)
        if hasattr(args, opt):
            value = getattr(args, opt)

        self.value = value

    def configure(self, parser: ArgumentParser) -> None:
        key = f"--{self.service.name}.rpc-host"
        help = (
            "TODO rpc-host option help"
        )
        parser.add_argument(key, type=str, help=help)
