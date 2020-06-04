from __future__ import annotations

from typing import TYPE_CHECKING

from .abc import PresetOption

if TYPE_CHECKING:
    from ..config import ParseResult
    from ..types import ArgumentParser


class BackupDirOption(PresetOption[str]):

    def parse(self, result: ParseResult) -> None:
        assert result.preset_conf
        assert result.command_line_args

        parsed = result.preset_conf
        args = result.command_line_args

        value = None

        if "backup-dir" in parsed:
            value = parsed["backup-dir"]

        opt = "backup_dir"
        if hasattr(args, opt):
            value = getattr(args, opt)

        self.value = value

    def configure(self, parser: ArgumentParser) -> None:
        help = (
            "The path to the directory to store your backup in. This should be "
            "located on an external drive, which usually is mounted in /mnt or "
            "/media."
        )
        parser.add_argument("--backup-dir", type=str, help=help)
