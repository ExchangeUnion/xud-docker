import os
import logging
import sys

from .config import Config
from .context import DockerContext


class Launcher:
    def __init__(self):
        self._logger = logging.getLogger("launcher.Launcher")

    def _emit_init_script(self):
        network = os.environ["NETWORK"]
        with open(os.path.dirname(__file__) + "/init.sh") as f:
            content = f.read()
            with open(f"/root/.xud-docker/{network}/init.sh", 'w') as f2:
                f2.write(content)

    def _print_banner(self):
        with open(os.path.dirname(__file__) + "/banner.txt") as f:
            print(f.read(), end="")
            sys.stdout.flush()

    def launch(self):
        network = os.environ["NETWORK"]
        network_dir = os.environ["NETWORK_DIR"]

        try:
            config = Config()
            config.parse()

            context = DockerContext(config)
            context.update()
            context.start()

            self._print_banner()
            self._emit_init_script()
        except KeyboardInterrupt:
            print()
            exit(130)  # follow bash return code convention 128 + 2(sigint)
        except:
            print(f"❌ Failed to launch {network} environment. For more details, see {network_dir}/{network}.log")
            self._logger.exception("Failed to launch")
            exit(1)
