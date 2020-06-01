from .abc import ServiceOption

class ExposePortsOption(ServiceOption):
    def parse(self, config: Config):
        node = self.node
        name = node.name
        parsed = config.network_config_file[name]
        args = config.command_line_arguments

        if "expose-ports" in parsed:
            value = parsed["expose-ports"]
            for p in value:
                p = PortPublish(str(p))
                if p not in node.ports:
                    node.ports.append(p)

        opt = "{}.expose-ports".format(name)
        if hasattr(args, opt):
            value = args[opt]
            for p in value.split(","):
                p = PortPublish(p.strip())
                if p not in node.ports:
                    node.ports.append(p)