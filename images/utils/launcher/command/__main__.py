import sys
import os
from ..config import Config
from ..context import DockerContext
from . import status, update

cmd = None

config = Config(args=os.environ["LAUNCH_ARGS"])
config.parse()

context = DockerContext(config)

if sys.argv[1] == "status":
    cmd = status(context)
elif sys.argv[1] == "update":
    cmd = update(context)
else:
    print("Command not found", file=sys.stderr)
    exit(1)

cmd.run(*sys.argv[2:])
