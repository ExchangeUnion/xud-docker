from .abc import ServiceOption

class ModeOption(ServiceOption):
    def parse(self, config: Config):
        node = self.node
        name = node.name
        parsed = config.network_config_file[name]
        args = config.command_line_arguments

        if "external" in parsed:
            print("Warning: Using deprecated option \"external\". Please use \"mode\" instead.")
            if parsed["external"]:
                node.mode = "external"

        if name in ["bitcoind", "litecoind"]:
            if "neutrino" in parsed:
                print("Warning: Using deprecated option \"neutrino\". Please use \"mode\" instead.")
                if parsed["neutrino"]:
                    node.mode = "neutrino"
            mode_values = ["native", "external", "neutrino", "light"]
        elif name == "geth":
            if "infura-project-id" in parsed:
                if "mode" not in parsed:
                    print("Warning: Please use option \"mode\" to specify Infura usage.")
                    node.mode = "infura"
            mode_values = ["native", "external", "infura", "light"]
        else:
            raise AssertionError("node should be bitcoind, litecoind or geth: " + name)

        if "mode" in parsed:
            value = parsed["mode"]
            if value not in mode_values:
                raise ValueError(value)
            node.mode = value

        opt = "{}.mode".format(name)
        if hasattr(args, opt):
            value = getattr(args, opt)
            if value not in mode_values:
                raise ValueError(value)
            node.mode = value