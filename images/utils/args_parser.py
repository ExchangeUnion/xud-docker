#!/usr/bin/env python3

from argparse import ArgumentParser
import os

parser = ArgumentParser(prog=os.environ["PROG"])
parser.add_argument("--branch", "-b")
parser.add_argument("--disable-update", action="store_true")
parser.add_argument("--simnet-dir")
parser.add_argument("--testnet-dir")
parser.add_argument("--mainnet-dir")
parser.add_argument("--external-ip")
parser.add_argument("--backup-dir")

try:
    args = parser.parse_args()
except:
    exit(1)
