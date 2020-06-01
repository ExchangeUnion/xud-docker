from .abc import ServiceOption


class AncientChaindataDirOption(ServiceOption):
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

        target = "/root/.ethereum-ancient-chaindata"

        if "ancient-chaindata-dir" in parsed:
            value = parsed["ancient-chaindata-dir"]
            self.update_volume(node.volumes, target, value)

        opt = "{}.ancient-chaindata-dir".format(name)
        if hasattr(args, opt):
            value = getattr(args, opt)
            self.update_volume(node.volumes, target, value)

    def configure(self, parser):
        pass

