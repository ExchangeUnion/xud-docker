from .abc import ServiceOption

class RpcUserOption(ServiceOption):
    def parse(self, config: Config):
        node = self.node
        name = node.name
        parsed = config.network_config_file[name]
        args = config.command_line_arguments

        if "rpc-user" in parsed:
            value = parsed["rpc-user"]
            # TODO rpc-user value validation
            node.external_rpc_user = value

        opt = "{}.rpc-user".format(name)
        if hasattr(args, opt):
            value = getattr(args, opt)
            node.external_rpc_user = value