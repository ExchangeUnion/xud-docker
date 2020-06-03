from __future__ import annotations

from typing import TYPE_CHECKING

from .abc import ServiceOption
from ..services import Bitcoind, Litecoind, Geth, Service
from ..types import VolumeMapping
from ...utils import ArgumentParser

if TYPE_CHECKING:
    from ..config import ParseResult


class DirOption(ServiceOption):

    def __init__(self, service: Service):
        assert isinstance(service, (Bitcoind, Litecoind, Geth)), "dir option is bitcoind, litecoind and geth only"
        super().__init__(service)

    def update_volume(self, volumes, container_dir, host_dir):
        target = [v for v in volumes if v.container_dir == container_dir]
        if len(target) == 0:
            volumes.append(VolumeMapping("{}:{}".format(host_dir, container_dir)))
        else:
            target = target[0]
            target.host_dir = host_dir

    def parse(self, result: ParseResult) -> None:
        assert result.preset_conf
        assert result.command_line_args

        service = self.service
        name = service.name
        parsed = result.preset_conf[name]
        args = result.command_line_args

        target = None

        if isinstance(service, Bitcoind):
            target = "/root/.bitcoin"
        elif isinstance(service, Litecoind):
            target = "/root/.litecoin"
        elif isinstance(service, Geth):
            target = "/root/.ethereum"

        assert target

        if "dir" in parsed:
            value = parsed["dir"]
            self.update_volume(service.container_spec.volumes, target, value)

        opt = "{}.dir".format(name)
        if hasattr(args, opt):
            value = getattr(args, opt)
            self.update_volume(service.container_spec.volumes, target, value)

    def configure(self, parser: ArgumentParser) -> None:
        key = f"--{self.service.name}.dir"
        help = (
            "This option specifies the container's volume mapping data "
            "directory. It will be ignored if you set below `external` or "
            "`neutrino` option to true."
        )
        parser.add_argument(key, type=str, help=help)

