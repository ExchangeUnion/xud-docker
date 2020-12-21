import argparse
import os
import platform

from launcher.service import ServiceManager
from .cleanup import CleanupCommand
from .gen import GenCommand
from .setup import SetupCommand


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

    manager = ServiceManager(network, network_dir)

    actions = {
        "gen": GenCommand(manager),
        "setup": SetupCommand(manager),
        "cleanup": CleanupCommand(manager),
    }

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action")
    for name, cmd in actions.items():
        cmd.configure_parser(subparsers.add_parser(name))

    args, unknown = parser.parse_known_args()

    actions[args.action].run(args)
