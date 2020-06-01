from .abc import ServiceOption

class RpcHostOption(ServiceOption):
    def parse(self, config: Config):
        node = self.node
        name = node.name
        parsed = config.network_config_file[name]
        args = config.command_line_arguments

        if "rpc-host" in parsed:
            value = parsed["rpc-host"]
            # TODO rpc-host value validation
            node.external_rpc_host = value

        opt = "{}.rpc-host".format(name)
        if hasattr(args, opt):
            value = getattr(args, opt)
            node.external_rpc_host = value