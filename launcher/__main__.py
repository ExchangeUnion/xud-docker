import sys
from launcher.cmd import run
import logging.config

logging.config.fileConfig(fname="log.ini")

logging.info("TEST!!!")

try:
    run()
except KeyboardInterrupt:
    print()
    sys.exit(130)  # 128 + SIGINT(2)
