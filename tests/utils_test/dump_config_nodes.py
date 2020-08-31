from typing import Any

from launcher.config import Config, ConfigLoader
from launcher.config.template import PortPublish
import json

config = Config(ConfigLoader())


class MyEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, PortPublish):
            return str(obj)
        return super().default(obj)


s = json.dumps(config.nodes, cls=MyEncoder)
print(s)
