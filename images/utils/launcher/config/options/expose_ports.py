from __future__ import annotations

from typing import TYPE_CHECKING

from .abc import ServiceOption
from ..services import Service, Geth
from ..types import PortPublish

if TYPE_CHECKING:
    from ..config import ParseResult
    from ..types import ArgumentParser


class ExposePortsOption(ServiceOption[str]):
    def parse(self, result: ParseResult) -> None:
        assert result.preset_conf
        assert result.command_line_args

        service = self.service
        name = service.name
        parsed = result.preset_conf[name]
        args = result.command_line_args

        if "expose-ports" in parsed:
            value = parsed["expose-ports"]
            for p in value:
                p = PortPublish(str(p))
                if p not in service.container_spec.ports:
                    service.container_spec.ports.append(p)

        opt = "{}.expose_ports".format(name)
        if hasattr(args, opt):
            value = args[opt]
            for p in value.split(","):
                p = PortPublish(p.strip())
                if p not in service.container_spec.ports:
                    service.container_spec.ports.append(p)

    def configure(self, parser: ArgumentParser) -> None:
        key = f"--{self.service.name}.expose-ports"
        help = (
            "TODO expose-port option help"
        )
        parser.add_argument(key, type=str, help=help)
