from .abc import ServiceOption

class RpcPortOption(ServiceOption):
    def parse(self, config: Config):
        node = self.node
        name = node.name
        parsed = config.network_config_file[name]
        args = config.command_line_arguments

        if "rpc-port" in parsed:
            value = parsed["rpc-port"]
            node.external_rpc_port = int(value)

        opt = "{}.rpc-port".format(name)
        if hasattr(args, opt):
            value = getattr(args, opt)
            node.external_rpc_port = int(value)