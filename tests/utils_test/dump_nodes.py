from typing import Any
from unittest.mock import patch, MagicMock
import docker.errors
import json
from launcher.node.base import ContainerSpec
from launcher.node.image import Image


def get_image(name):
    raise docker.errors.ImageNotFound(name)


def fake_from_env(timeout=None):
    mock = MagicMock()
    mock.images.get = get_image
    return mock


def normalize_volumes(volumes):
    result = []
    for key, value in volumes.items():
        if value["mode"] == "rw":
            result.append("%s:%s" % (key, value["bind"]))
    return result


def normalize_ports(ports):
    result = []
    for key, value in ports.items():
        key = key.replace("/tcp", "")
        result.append("%s:%s" % (value, key))
    return result


class MyEncoder(json.JSONEncoder):

    def default(self, o: Any) -> Any:
        if isinstance(o, ContainerSpec):
            d = vars(o)
            d["volumes"] = normalize_volumes(d["volumes"])
            d["ports"] = normalize_ports(d["ports"])
            return d
        elif isinstance(o, Image):
            return o.use_image
        return super().default(o)


with patch("docker.from_env", fake_from_env):
    from launcher.config import Config, ConfigLoader
    from launcher import XudEnv
    import json
    config = Config(ConfigLoader())
    env = XudEnv(config, None)
    nodes = env.node_manager.nodes
    result = {key: value.container_spec for key, value in nodes.items()}
    s = json.dumps(result, cls=MyEncoder)
    print(s)
