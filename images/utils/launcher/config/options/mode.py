from __future__ import annotations

from typing import TYPE_CHECKING

from .abc import ServiceOption

if TYPE_CHECKING:
    from ..config import ParseResult
    from ...utils import ArgumentParser


class ModeOption(ServiceOption):
    def parse(self, result: ParseResult) -> None:
        assert result.preset_conf
        assert result.command_line_args

        service = self.service
        name = service.name
        parsed = result.preset_conf[name]
        args = result.command_line_args

        value = None

        if "external" in parsed:
            print("Warning: Using deprecated option \"external\". Please use \"mode\" instead.")
            if parsed["external"]:
                value = "external"

        if name in ["bitcoind", "litecoind"]:
            if "neutrino" in parsed:
                print("Warning: Using deprecated option \"neutrino\". Please use \"mode\" instead.")
                if parsed["neutrino"]:
                    value = "neutrino"
            mode_values = ["native", "external", "neutrino", "light"]
        elif name == "geth":
            if "infura-project-id" in parsed:
                if "mode" not in parsed:
                    print("Warning: Please use option \"mode\" to specify Infura usage.")
                    value = "infura"
            mode_values = ["native", "external", "infura", "light"]
        else:
            raise AssertionError("node should be bitcoind, litecoind or geth: " + name)

        if "mode" in parsed:
            value = parsed["mode"]
            if value not in mode_values:
                raise ValueError(value)

        opt = "{}.mode".format(name)
        if hasattr(args, opt):
            value = getattr(args, opt)
            if value not in mode_values:
                raise ValueError(value)

        self.value = value

    def configure(self, parser: ArgumentParser) -> None:
        key = f"--{self.service.name}.mode"
        help = (
            "TODO mode option help"
        )
        parser.add_argument(key, type=str, help=help)
