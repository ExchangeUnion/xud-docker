from .toolkit import Toolkit
import logging
import os

logfile = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools.log")
FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

logging.basicConfig(filename=logfile, level=logging.DEBUG, format=FORMAT, filemode="w")
