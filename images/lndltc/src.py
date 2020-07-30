from tools.core import src


class SourceManager(src.SourceManager):
    def __init__(self):
        super().__init__("https://github.com/ltcsuite/lnd")

    def get_build_args(self, version):
        tags = [
            "autopilotrpc",
            "chainrpc",
            "invoicesrpc",
            "routerrpc",
            "signrpc",
            "walletrpc",
            "watchtowerrpc",
            "wtclientrpc",
            "experimental",
        ]
        args = {
            "TAGS": " ".join(tags),
            "LDFLAGS": "-X github.com/ltcsuite/lnd/build.Commit={}".format(self.get_ref(version)),
        }

        return args

    def get_ref(self, version):
        if version == "latest":
            return "v0.10.1-beta"
        else:
            return super().get_ref(version)
