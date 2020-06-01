from .abc import ServiceOption

class InfuraProjectIdOption(ServiceOption):
    def parse(self, config: Config):
        node = self.node
        name = node.name
        parsed = config.network_config_file[name]
        args = config.command_line_arguments

        if "infura-project-id" in parsed:
            value = parsed["infura-project-id"]
            # TODO zmqpubrawtx value validation
            node.infura_project_id = value

        # parse command-line option "--node.zmqpubrawtx"
        opt = "{}.infura-project-id".format(name)
        if hasattr(args, opt):
            value = getattr(args, opt)
            node.infura_project_id = value