from tools.core import src
import os


class SourceManager(src.SourceManager):
    def __init__(self):
        super().__init__(None)
        self.lnd_dir = os.path.join(self.src_dir, "lnd")
        self.lnd_ltc_dir = os.path.join(self.src_dir, "lnd-ltc")

    def ensure(self, version):
        if "ltc" in version:
            repo_dir = self.lnd_ltc_dir
            self.ensure_repo("https://github.com/ltcsuite/lnd", repo_dir)
            version = version.replace("-ltc", "")
            version = version.replace("-simnet", "")
            self.checkout(repo_dir, version)
        else:
            repo_dir = self.lnd_dir
            self.ensure_repo("https://github.com/lightningnetwork/lnd", repo_dir)
            version = version.replace("-simnet", "")
            self.checkout(repo_dir, version)

    def get_dockerfile(self, version):
        if version.endswith("-simnet"):
            return "simnet.Dockerfile"
        else:
            return "Dockerfile"

    def get_build_args(self, version):
        tags = [
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
            "TAGS": " ".join(tags)
        }
        if "ltc" in version:
            args["SRC_DIR"] = ".src/lnd-ltc"
            if version.endswith("-simnet"):
                args["PATCHES_DIR"] = "patches-ltc"
                args["ENTRYPOINT_FILE"] = "entrypoint-ltc-simnet.sh"
            else:
                args["ENTRYPOINT_FILE"] = "entrypoint-ltc.sh"
                args["LND_CONF_FILE"] = "lnd-ltc.conf"
            args["LDFLAGS"] = f"-X github.com/ltcsuite/lnd/build.Commit={version}"
        else:
            args["SRC_DIR"] = ".src/lnd"
            if version.endswith("-simnet"):
                args["PATCHES_DIR"] = "patches"
                args["ENTRYPOINT_FILE"] = "entrypoint-simnet.sh"
            else:
                args["ENTRYPOINT_FILE"] = "entrypoint.sh"
                args["LND_CONF_FILE"] = "lnd.conf"
            args["LDFLAGS"] = f"-X github.com/lightningnetwork/lnd/build.Commit={version}"
        return args

    def get_application_revision(self, version):
        if "ltc" in version:
            return self.get_revision(self.lnd_ltc_dir)
        else:
            return self.get_revision(self.lnd_dir)
