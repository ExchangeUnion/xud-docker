from subprocess import Popen, PIPE, STDOUT
import sys

from .context import context
from .errors import FatalError


def run_command(cmd, errmsg):
    if context.dry_run:
        print("[dry-run] $ " + cmd)
        return
    else:
        print("\n$ " + cmd)

    p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)

    for line in p.stdout:
        print(line.decode(), end="")
    sys.stdout.flush()

    exit_code = p.wait()

    if exit_code != 0:
        raise FatalError("{} (exit code is {})".format(errmsg, exit_code))
