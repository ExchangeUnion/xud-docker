from __future__ import annotations

from typing import TYPE_CHECKING

from .abc import ServiceOption
from ..services import Service, Geth
from ..types import VolumeMapping

if TYPE_CHECKING:
    from ..config import ParseResult
    from ..types import ArgumentParser


class AncientChaindataDirOption(ServiceOption[str]):
    def __init__(self, service: Service):
        assert isinstance(service, Geth), "ancient-chaindata-dir option is geth only"
        super().__init__(service)

    @staticmethod
    def update_volume(volumes, container_dir, host_dir):
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

        target = "/root/.ethereum-ancient-chaindata"
        value = None

        if "ancient-chaindata-dir" in parsed:
            value = parsed["ancient-chaindata-dir"]
            self.update_volume(service.container_spec.volumes, target, value)

        opt = "{}.ancient_chaindata_dir".format(name)
        if hasattr(args, opt):
            value = getattr(args, opt)
            self.update_volume(service.container_spec.volumes, target, value)

        self.value = value

    def configure(self, parser: ArgumentParser) -> None:
        key = f"--{self.service.name}.ancient-chaindata-dir"
        help = (
            "This option specifies the container's volume mapping ancient "
            "chaindata directory. Can be located on a slower HDD."
        )
        parser.add_argument(key, type=str, help=help)
