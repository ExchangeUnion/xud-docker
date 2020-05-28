import logging

from .context import Context
from .service import Service
from .image import Image, ImageStatus
from .container import Container, ContainerStatus
from .types import XudNetwork

logging.basicConfig(filename="tests-core.log")
logging.getLogger("tests").setLevel(logging.DEBUG)
