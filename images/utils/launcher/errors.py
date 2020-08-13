from enum import Enum
from typing import Optional


class FatalError(Exception):
    pass


class ConfigErrorScope(Enum):
    COMMAND_LINE_ARGS = 0
    GENERAL_CONF = 1
    NETWORK_CONF = 2


class ConfigError(Exception):
    def __init__(self, scope: ConfigErrorScope, conf_file: Optional[str] = None):
        super().__init__(scope)
        self.scope = scope
        self.conf_file = conf_file


class ParseError(Exception):
    pass


class IllegalState(Exception):
    pass
