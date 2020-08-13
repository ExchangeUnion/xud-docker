import logging
from .Launcher import Launcher

fmt = "%(asctime)s.%(msecs)03d %(levelname)s %(process)d --- [%(threadName)s] %(name)s: %(message)s"
datefmt = "%Y-%m-%d %H:%M:%S"
logging.basicConfig(format=fmt, datefmt=datefmt, level=logging.ERROR, filename="/var/log/launcher.log")
logging.getLogger(__name__).setLevel(logging.DEBUG)
