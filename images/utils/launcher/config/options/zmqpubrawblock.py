from .abc import ServiceOption

class ZmqpubrawblockOption(ServiceOption):
    def parse(self, config: Config):
        node = self.node
        name = node.name
        parsed = config.network_config_file[name]
        args = config.command_line_arguments

        if "zmqpubrawblock" in parsed:
            value = parsed["zmqpubrawblock"]
            # TODO zmqpubrawblock value validation
            node.external_zmqpubrawblock = value

        # parse command-line option "--node.zmqpubrawblock"
        opt = "{}.zmqpubrawblock".format(name)
        if hasattr(args, opt):
            value = getattr(args, opt)
            node.external_zmqpubrawblock = value