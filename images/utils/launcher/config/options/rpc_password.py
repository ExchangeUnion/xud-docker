from .abc import ServiceOption

class RpcPasswordOption(ServiceOption):
    def parse(self, config: Config):
        node = self.node
        name = node.name
        parsed = config.network_config_file[name]
        args = config.command_line_arguments

        if "rpc-password" in parsed:
            value = parsed["rpc-password"]
            # TODO rpc-password value validation
            node.external_rpc_password = value

        # parse command-line option "--node.rpc-password"
        opt = "{}.rpc-password".format(name)
        if hasattr(args, opt):
            value = getattr(args, opt)
            node.external_rpc_password = value