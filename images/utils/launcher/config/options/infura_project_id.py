from __future__ import annotations

from typing import TYPE_CHECKING

from .abc import ServiceOption
from ..services import Geth, Service

if TYPE_CHECKING:
    from ..config import ParseResult
    from ...utils import ArgumentParser


class InfuraProjectIdOption(ServiceOption):
    def __init__(self, service: Service):
        assert isinstance(service, Geth), "infura-project-id is geth only"
        super().__init__(service)

    def parse(self, result: ParseResult) -> None:
        assert result.preset_conf
        assert result.command_line_args

        service = self.service
        name = service.name
        parsed = result.preset_conf[name]
        args = result.command_line_args

        value = None

        if "infura-project-id" in parsed:
            value = parsed["infura-project-id"]

        opt = "{}.infura_project_id".format(name)
        if hasattr(args, opt):
            value = getattr(args, opt)

        self.value = value

    def configure(self, parser: ArgumentParser) -> None:
        key = f"--{self.service.name}.infura-project-id"
        help = (
            "TODO infura-project-id option help"
        )
        parser.add_argument(key, type=str, help=help)
