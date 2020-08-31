from unittest.mock import patch


def fake_from_env():
    print("fake")


with patch("docker.from_env", fake_from_env):
    from launcher.config import Config, ConfigLoader
    from launcher import XudEnv
    import json
    config = Config(ConfigLoader())
    env = XudEnv(config, None)
    xud = env.node_manager.get_node("xud")
    spec = xud.container_spec
    s = json.dumps(spec)
    print(s)
