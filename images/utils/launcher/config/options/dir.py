from .abc import ServiceOption

class DirOption(ServiceOption):

    def update_volume(self, volumes, container_dir, host_dir):
        target = [v for v in volumes if v.container_dir == container_dir]
        if len(target) == 0:
            volumes.append(VolumeMapping("{}:{}".format(host_dir, container_dir)))
        else:
            target = target[0]
            target.host_dir = host_dir

    def parse(self, config: Config):
        node = self.node
        name = node.name
        parsed = config.network_config_file[name]
        args = config.command_line_arguments

        if name == "bitcoind":
            target = "/root/.bitcoin"
        elif name == "litecoind":
            target = "/root/.litecoin"
        elif name == "geth":
            target = "/root/.ethereum"
        else:
            raise AssertionError("name should be bitcoind, litecoind or geth: " + name)

        if "dir" in parsed:
            value = parsed["dir"]
            self.update_volume(node.volumes, target, value)

        opt = "{}.dir".format(name)
        if hasattr(args, opt):
            value = getattr(args, opt)
            self.update_volume(node.volumes, target, value)