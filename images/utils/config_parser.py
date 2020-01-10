#!/usr/bin/env python3

import argparse
import toml
import os


def _parse_xud_docker_conf():
    with open("/root/.xud-docker/xud-docker.conf") as f:
        return toml.load(f.read())


home_dir = os.environ["HOME_DIR"]
network = os.environ["NETWORK"]
network_dir = home_dir + "/" + network
backup_dir = None

try:
    parsed = _parse_xud_docker_conf()
    value = parsed[f"{network}-dir"]
    if value != network_dir:
        network_dir = value
    backup_dir = parsed["backup-dir"]
except:
    pass

parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
parser.add_argument(f"--{network}-dir")
parser.add_argument(f"--backup-dir")
args, unknown = parser.parse_known_args()

if hasattr(args, f"{network}_dir"):
    network_dir = getattr(args, f"{network}_dir")
if hasattr(args, "backup_dir"):
    backup_dir = getattr(args, "backup_dir")

result = f"NETWORK_DIR={network_dir}"
if backup_dir:
    result += f" && BACKUP_DIR={backup_dir}"
print(result)
