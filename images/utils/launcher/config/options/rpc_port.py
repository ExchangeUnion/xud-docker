from __future__ import annotations

from typing import TYPE_CHECKING

from .abc import ServiceOption

if TYPE_CHECKING:
    from ..config import ParseResult
    from ..types import ArgumentParser


class RpcPortOption(ServiceOption[int]):
    def parse(self, result: ParseResult) -> None:
        assert result.preset_conf
        assert result.command_line_args

        service = self.service
        name = service.name
        parsed = result.preset_conf[name]
        args = result.command_line_args

        value = None

        if "rpc-port" in parsed:
            value = int(parsed["rpc-port"])

        opt = "{}.rpc_port".format(name)
        if hasattr(args, opt):
            value = int(getattr(args, opt))

        self.value = value

    def configure(self, parser: ArgumentParser) -> None:
        key = f"--{self.service.name}.rpc-port"
        help = (
            "TODO rpc-port option help"
        )
        parser.add_argument(key, type=str, help=help)
