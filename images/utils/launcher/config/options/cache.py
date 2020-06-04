from __future__ import annotations

from typing import TYPE_CHECKING

from .abc import ServiceOption
from ..services import Geth, Service

if TYPE_CHECKING:
    from ..config import ParseResult
    from ..types import ArgumentParser


class CacheOption(ServiceOption[int]):

    def __init__(self, service: Service):
        assert isinstance(service, Geth), "cache option is geth only"
        super().__init__(service)

    def parse(self, result: ParseResult) -> None:
        assert result.preset_conf
        assert result.command_line_args

        service = self.service
        name = service.name
        parsed = result.preset_conf[name]
        args = result.command_line_args

        value = 256

        if "cache" in parsed:
            value = int(parsed["cache"])

        opt = "{}.cache".format(name)
        if hasattr(args, opt):
            value = int(getattr(args, opt))

        self.value = value

    def configure(self, parser: ArgumentParser) -> None:
        key = f"--{self.service.name}.cache"
        help = (
            "This option specifies the geth performance tuning option "
            "`--cache`. The default value in our setup is 256, which keeps RAM "
            "consumption ~4 GB, max value is 10240. The more, the faster the "
            "initial sync."
        )
        parser.add_argument(key, type=int, help=help)
