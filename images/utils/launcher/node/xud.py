import json
from .base import Node, CliBackend, CliError
import re


class XudApiError(Exception):
    pass


class XudApi:
    def __init__(self, backend):
        self._backend = backend

    def getinfo(self):
        try:
            s = self._backend["getinfo -j"]()
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


class Xud(Node):
    def __init__(self, name, ctx):
        super().__init__(name, ctx)

        self._cli = "xucli"

        self.api = XudApi(CliBackend(self.client, self.container_name, self._logger, self._cli))

    def status(self):
        status = super().status()
        if status == "exited":
            # TODO analyze exit reason
            return "Container exited"
        elif status == "running":
            try:
                info = self.api.getinfo()
                lndbtc_status = info["lndMap"][0][1]["status"]
                lndltc_status = info["lndMap"][1][1]["status"]
                raiden_status = info["raiden"]["status"]

                if "has no active channels" in lndbtc_status \
                        or "has no active channels" in lndltc_status \
                        or "has no active channels" in raiden_status:
                    return "Waiting for channels"

                if "Ready" == lndbtc_status \
                        and "Ready" == lndltc_status \
                        and "Ready" == raiden_status:
                    return "Ready"
                else:
                    not_ready = []
                    if lndbtc_status != "Ready":
                        not_ready.append("lndbtc")
                    if lndltc_status != "Ready":
                        not_ready.append("lndltc")
                    if raiden_status != "Ready":
                        not_ready.append("raiden")
                    return "Waiting for " + ", ".join(not_ready)
            except XudApiError as e:
                if "xud is locked" in str(e):
                    return "Wallet locked. Unlock with xucli unlock."
                elif "no such file or directory, open '/root/.xud/tls.cert'" in str(e):
                    return "Starting"
                else:
                    return str(e)
            except:
                self._logger.exception("Failed to get advanced running status")
                return "Container running"
        else:
            return status

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
                return Exception("Unexpected xucli create error happens")
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
                return Exception("Unexpected xucli restore error")
