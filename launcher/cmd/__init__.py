import argparse
import logging
import os
import platform
import sys
from datetime import datetime

from launcher.core import Launcher
from .attach import Attach
from .cleanup import Cleanup
from .console import Console
from .gen import Gen
from .setup import Setup


def get_home_dir():
    p = platform.system()
    if p == "Linux":
        return os.path.expanduser("~/.xud-docker")
    elif p == "Darwin":
        return os.path.expanduser("~/Library/Application Support/XudDocker")
    elif p == "Windows":
        return os.path.expanduser("~/AppData/Local/XudDocker")


def run():
    home_dir = get_home_dir()
    network = os.getenv("NETWORK") or "mainnet"
    network_dir = os.getenv("NETWORK_DIR") or os.path.join(home_dir, network)
    logs_dir = os.path.join(network_dir, "logs")
    logfile = os.path.join(logs_dir, "launcher-%s.log" % int(datetime.now().timestamp()))
    logfmt = "%(asctime)s %(levelname)5s %(process)d --- [%(threadName)16s] %(name)32s: %(message)s"
    logging.basicConfig(filename=logfile, format=logfmt, level=logging.INFO)
    logging.getLogger("launcher").setLevel(logging.DEBUG)

    launcher = Launcher(network, network_dir)

    actions = {
        "gen": Gen(launcher),
        "setup": Setup(launcher),
        "cleanup": Cleanup(launcher),
        "attach": Attach(launcher),
        "console": Console(launcher),
    }

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action")
    for name, cmd in actions.items():
        cmd.configure_parser(subparsers.add_parser(name))

    args, unknown = parser.parse_known_args()

    logger = logging.getLogger("launcher.cmd")

    try:
        actions[args.action].run(args)
    except KeyboardInterrupt:
        sys.exit(130)  # 128 + SIGINT(2)
    except Exception as e:
        logger.exception("Failed to run command: %s", args.action)
        msg = str(e).strip()
        if msg == "":
            msg = "<no message>"
        else:
            msg = str(e)
        print("%s: %s. For more details, see %s." % (e.__class__.__name__, msg, logfile))
        sys.exit(1)
