from logging import getLogger
import traceback
import sys

from .shell import Shell
from .config import Config, ConfigLoader
from .XudEnv import XudEnv
from .errors import ConfigError, ConfigErrorScope, FatalError

__all__ = ["Launcher"]

logger = getLogger(__name__)


class Launcher:
    def __init__(self):
        try:
            self.config = Config(ConfigLoader())
        except ConfigError as e:
            if e.scope == ConfigErrorScope.COMMAND_LINE_ARGS:
                print("Failed to parse command-line arguments, exiting.")
                print(f"{e.__cause__}")
            elif e.scope == ConfigErrorScope.GENERAL_CONF:
                print("Failed to parse config file {}, exiting.".format(e.conf_file))
                print(f"{e.__cause__}")
            elif e.scope == ConfigErrorScope.NETWORK_CONF:
                print("Failed to parse config file {}, exiting.".format(e.conf_file))
                print(f"{e.__cause__}")
            sys.exit(1)

    def launch(self) -> None:
        shell = Shell()
        shell.set_network_dir(self.config.network_dir)  # create shell history file in network_dir
        try:
            env = XudEnv(self.config, shell)
            env.start()
        except KeyboardInterrupt:
            print()
            sys.exit(1)
        except FatalError as e:
            print(f"Error: {e}. For more details, see {self.config.logfile}")
            sys.exit(1)
        except:
            logger.exception("Unexpected exception during launching")
            traceback.print_exc()
            sys.exit(1)
        finally:
            shell.stop()

    def export(self) -> str:
        env = XudEnv(self.config, None)
        return env.export()
