from .abc import ServiceOption

class ZmqpubrawtxOption(ServiceOption):
    def parse(self, config: Config):
        node = self.node
        name = node.name
        parsed = config.network_config_file[name]
        args = config.command_line_arguments

        if "zmqpubrawtx" in parsed:
            value = parsed["zmqpubrawtx"]
            # TODO zmqpubrawtx value validation
            node.external_zmqpubrawtx = value

        # parse command-line option "--node.zmqpubrawtx"
        opt = "{}.zmqpubrawtx".format(name)
        if hasattr(args, opt):
            value = getattr(args, opt)
            node.external_zmqpubrawtx = value