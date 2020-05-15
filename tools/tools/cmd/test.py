import os
import sys

from ..context import context


class TestCommand:
    def __init__(self, parser):
        parser.add_argument("-d", "--debug", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def run(self, args):
        context.debug = args.debug
        context.dry_run = args.dry_run
        cwd = os.getcwd()
        try:
            os.chdir(context.project_dir)
            exit_code = os.system("python3.8 -m pytest -s")
            if exit_code != 0:
                sys.exit(1)
        finally:
            os.chdir(cwd)
