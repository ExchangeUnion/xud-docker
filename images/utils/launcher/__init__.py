import logging
import os


FORMAT = "%(asctime)s.%(msecs)03d %(levelname)s %(process)d --- [%(threadName)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
NETWORK = os.environ["NETWORK"]
LOG_TIMESTAMP = os.environ["LOG_TIMESTAMP"]
LOGFILE = f"/root/.xud-docker/{NETWORK}/{NETWORK}-{LOG_TIMESTAMP}.log"
logging.basicConfig(format=FORMAT, datefmt=DATE_FORMAT, level=logging.ERROR, filename=LOGFILE)

level_config = {
    "launcher": logging.DEBUG,
}

for logger, level in level_config.items():
    logging.getLogger(logger).setLevel(level)
