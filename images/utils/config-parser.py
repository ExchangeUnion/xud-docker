#!/usr/bin/env python3

import sys
import argparse
import toml


def bool_str(val):
    if val is None:
        return None
    if val:
        return "true"
    else:
        return "false"


default_config_vars = {
    "DEBUG": "false",
    "BRANCH": "master",
    "HOME_DIR": "$HOME/.xud-docker",
    "NETWORK_DIR": "$HOME_DIR/$NETWORK",
    "PROJECT_DIR": None,
    "BITCOIND_DIR": "$NETWORK_DIR/data/bitcoind",
    "LITECOIND_DIR": "$NETWORK_DIR/data/litecoind",
    "GETH_DIR": "$NETWORK_DIR/data/geth",
    "GETH_CHAINDATA_DIR": "$NETWORK_DIR/data/geth/chaindata",
    "LOGFILE": "$NETWORK_DIR/xud-docker.log",
    "DISABLE_UPDATES": "false",
    "CONFIG":  "$HOME_DIR/xud-docker.conf",
}

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--debug', action='store_const', const="true", default=None)
parser.add_argument('-b', '--branch')
parser.add_argument('--project-dir')
parser.add_argument('--home-dir')
parser.add_argument('--bitcoind-dir')
parser.add_argument('--litecoind-dir')
parser.add_argument('--geth-dir')
parser.add_argument('--geth-chaindata-dir')
parser.add_argument('--logfile')
parser.add_argument('--disable-updates', action='store_const', const="true", default=None)
parser.add_argument('-c', '--config')
args = parser.parse_args()

args_config_vars = {
    "DEBUG": args.debug,
    "BRANCH": args.branch,
    "HOME_DIR": args.home_dir,
    "NETWORK_DIR": None,
    "PROJECT_DIR": args.project_dir,
    "BITCOIND_DIR": args.bitcoind_dir,
    "LITECOIND_DIR": args.litecoind_dir,
    "GETH_DIR": args.geth_dir,
    "GETH_CHAINDATA_DIR": args.geth_chaindata_dir,
    "LOGFILE": args.logfile,
    "DISABLE_UPDATES": args.disable_updates,
    "CONFIG":  args.config,
}


parsed_toml = toml.load(sys.stdin)

file_config_vars = {
    "DEBUG": bool_str(parsed_toml.get("debug", None)),
    "BRANCH": parsed_toml.get("branch", None),
    "HOME_DIR": parsed_toml.get("home-dir", None) if args_config_vars["CONFIG"] else None,
    "NETWORK_DIR": None,
    "PROJECT_DIR": parsed_toml.get("project-dir", None),
    "BITCOIND_DIR": parsed_toml.get("bitcoind", None) and parsed_toml.get("bitcoind").get("dir", None),
    "LITECOIND_DIR": parsed_toml.get("litecoind", None) and parsed_toml.get("litecoind").get("dir", None),
    "GETH_DIR": parsed_toml.get("geth", None) and parsed_toml.get("geth").get("dir", None),
    "GETH_CHAINDATA_DIR": parsed_toml.get("geth", None) and parsed_toml.get("geth").get("chaindata-dir", None),
    "LOGFILE": parsed_toml.get("logfile", None),
    "DISABLE_UPDATES": bool_str(parsed_toml.get("disable-updates", None)),
    "CONFIG": None
}

keys = [
    "DEBUG", "BRANCH", "HOME_DIR", "NETWORK_DIR", "PROJECT_DIR",
    "BITCOIND_DIR", "LITECOIND_DIR", "GETH_DIR", "GETH_CHAINDATA_DIR",
    "LOGFILE", "DISABLE_UPDATES", "CONFIG"
]

for key in keys:
    value = args_config_vars[key] or file_config_vars[key] or default_config_vars[key]
    if value:
        print("%s=\"%s\"" % (key, value))
