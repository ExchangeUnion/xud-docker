from typing import Any
from unittest.mock import patch, MagicMock
import docker.errors
import json
from launcher.node.base import ContainerSpec
from launcher.node.image import Image
from launcher.node.xud import Xud
from launcher.config import Config


def get_image(name):
    raise docker.errors.ImageNotFound(name)


def fake_from_env(timeout=None):
    mock = MagicMock()
    mock.images.get = get_image
    return mock


class MyEncoder(json.JSONEncoder):

    def default(self, o: Any) -> Any:
        if isinstance(o, ContainerSpec):
            d = vars(o)
            return d
        elif isinstance(o, Image):
            d = vars(o)
            d.pop("logger")
            return d
        elif isinstance(o, Xud):
            return "xud"
        elif isinstance(o, MagicMock):
            return "mock"
        elif isinstance(o, Config):
            return "config"
        return super().default(o)


with patch("docker.from_env", fake_from_env):
    from launcher.config import Config, ConfigLoader
    from launcher import XudEnv
    import json
    config = Config(ConfigLoader())
    env = XudEnv(config, None)
    xud = env.node_manager.get_node("xud")
    spec = xud.container_spec
    s = json.dumps(spec, cls=MyEncoder)
    print(s)
