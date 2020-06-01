from .abc import PresetOption
from ..config import ParseResult


class BackupDirOption(PresetOption):

    def parse(self, result: ParseResult):
        pass

    def configure(self, parser):
        pass
