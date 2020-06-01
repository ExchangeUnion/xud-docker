from .abc import ServiceOption

class InfuraProjectSecretOption(ServiceOption):
    def parse(self, config: Config):
        node = self.node
        name = node.name
        parsed = config.network_config_file[name]
        args = config.command_line_arguments

        if "infura-project-secret" in parsed:
            value = parsed["infura-project-secret"]
            # TODO zmqpubrawtx value validation
            node.infura_project_secret = value

        # parse command-line option "--node.zmqpubrawtx"
        opt = "{}.infura-project-secret".format(name)
        if hasattr(args, opt):
            value = getattr(args, opt)
            node.infura_project_secret = value