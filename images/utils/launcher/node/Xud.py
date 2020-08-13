import json
import re

from .Node import Node, NodeApi, CliError


class XudApiError(Exception):
    pass


class XudApi(NodeApi):
    def getinfo(self):
        try:
            s = self.cli("getinfo -j")
            s = re.sub(r"D.*Warning: insecure environment read function 'getenv' used[\s\n\r]+", "", s)
            return json.loads(s)
        except CliError as e:
            raise XudApiError(e.output)


class PasswordNotMatch(Exception):
    pass


class MnemonicNot24Words(Exception):
    pass


class InvalidPassword(Exception):
    pass


class NoWalletsInitialized(Exception):
    pass


class Xud(Node[XudApi]):
    def __init__(self, name, ctx):
        super().__init__(name, ctx)
        self.container_spec.environment.append("NODE_ENV=production")

    @property
    def cli_prefix(self):
        return "xucli"

    def application_status(self):
        try:
            info = self.api.getinfo()
            lndbtc_status = info["lndMap"][0][1]["status"]
            lndltc_status = info["lndMap"][1][1]["status"]
            connext_status = info["connext"]["status"]

            if "has no active channels" in lndbtc_status \
                    or "has no active channels" in lndltc_status \
                    or "has no active channels" in connext_status:
                return "Waiting for channels"

            if "Ready" == lndbtc_status \
                    and "Ready" == lndltc_status \
                    and "Ready" == connext_status:
                return "Ready"
            else:
                not_ready = []
                if lndbtc_status != "Ready":
                    not_ready.append("lndbtc")
                if lndltc_status != "Ready":
                    not_ready.append("lndltc")
                if connext_status != "Ready":
                    not_ready.append("connext")
                return "Waiting for " + ", ".join(not_ready)
        except XudApiError as e:
            if "xud is locked" in str(e):
                return "Wallet locked. Unlock with xucli unlock."
            elif "no such file or directory, open '/root/.xud/tls.cert'" in str(e):
                return "Starting..."
            elif "xud is starting" in str(e):
                return "Starting..."
            else:
                return str(e)
        except:
            self.logger.exception("Failed to get advanced running status")
            return "Waiting for xud to come up..."

    def cli_filter(self, cmd, text):
        text = re.sub(r"D.*Warning: insecure environment read function 'getenv' used[\s\n\r]+", "", text)
        return text

    def extract_exception(self, cmd: str, output: str):
        if cmd.startswith("create"):
            if "password must be at least 8 characters" in output:
                return InvalidPassword()
            elif "Passwords do not match, please try again" in output:
                return PasswordNotMatch()
            elif "xud was initialized without a seed because no wallets could be initialized" in output:
                return NoWalletsInitialized()
            elif "it is your ONLY backup in case of data loss" in output:
                return None
            else:
                return Exception("Unexpected xucli create error: " + output.strip())
        elif cmd.startswith("restore"):
            if "Password must be at least 8 characters" in output:
                return InvalidPassword()
            elif "Passwords do not match, please try again" in output:
                return PasswordNotMatch()
            elif "Mnemonic must be exactly 24 words" in output:
                return MnemonicNot24Words()
            elif "The following wallets were restored" in output:
                return None
            else:
                return Exception("Unexpected xucli restore error: " + output.strip())
        elif cmd.startswith("unlock"):
            if "xud was unlocked succesfully" in output:
                return None
            elif output == "Enter master xud password: ":
                return KeyboardInterrupt()
            else:
                return Exception("Unexpected xucli unlock error: " + output.strip())
