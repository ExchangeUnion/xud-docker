from shutil import copyfile
import os

from ..errors import FatalError
from ..utils import normalize_path, get_hostfs_file

__all__ = ["ConfigLoader"]


class ConfigLoader:
    def load_general_config(self, home_dir):
        config_file = get_hostfs_file(f"{home_dir}/xud-docker.conf")
        sample_config_file = get_hostfs_file(f"{home_dir}/sample-xud-docker.conf")
        copyfile(os.path.dirname(__file__) + "/xud-docker.conf", sample_config_file)
        if os.path.exists(config_file):
            with open(config_file) as f:
                return f.read()
        return ""

    def load_network_config(self, network, network_dir):
        config_file = get_hostfs_file(f"{network_dir}/{network}.conf")
        sample_config_file = get_hostfs_file(f"{network_dir}/sample-{network}.conf")
        copyfile(os.path.dirname(__file__) + f'/{network}.conf', sample_config_file)
        if os.path.exists(config_file):
            with open(config_file) as f:
                return f.read()
        return ""

    def load_lndenv(self, network_dir):
        lndenv = get_hostfs_file(f"{network_dir}/lnd.env")
        try:
            with open(lndenv) as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def ensure_home_dir(self, host_home):
        home_dir = host_home + "/.xud-docker"
        hostfs_dir = get_hostfs_file(home_dir)
        if os.path.exists(hostfs_dir):
            if not os.path.isdir(hostfs_dir):
                raise FatalError("{} is not a directory".format(home_dir))
            else:
                if not os.access(hostfs_dir, os.R_OK):
                    raise FatalError("{} is not readable".format(home_dir))
                if not os.access(hostfs_dir, os.W_OK):
                    raise FatalError("{} is not writable".format(home_dir))
        else:
            os.mkdir(hostfs_dir)
        return home_dir

    def ensure_network_dir(self, network_dir):
        network_dir = normalize_path(network_dir)
        hostfs_dir = get_hostfs_file(network_dir)
        if os.path.exists(hostfs_dir):
            if not os.path.isdir(hostfs_dir):
                raise FatalError("{} is not a directory".format(network_dir))
            else:
                if not os.access(hostfs_dir, os.R_OK):
                    raise FatalError("{} is not readable".format(network_dir))
                if not os.access(hostfs_dir, os.W_OK):
                    raise FatalError("{} is not writable".format(network_dir))
        else:
            os.makedirs(hostfs_dir)

        if not os.path.exists(hostfs_dir + "/logs"):
            os.mkdir(hostfs_dir + "/logs")
        return network_dir
