from argparse import ArgumentParser

from .test_custom_network_dir import test

parser = ArgumentParser()
parser.add_argument("-b", "--branch")

args = parser.parse_args()

test(args.branch)
