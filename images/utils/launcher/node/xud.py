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

        if self.network == "simnet":
            self._cli = "xucli --rpcport=28886"
        else:
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
                lndbtc_ready = info["lndMap"][0][1]["status"] == "Ready"
                lndltc_ready = info["lndMap"][1][1]["status"] == "Ready"
                raiden_ready = info["raiden"]["status"] == "Ready"
                if self.network in ["testnet", "mainnet"]:
                    lndbtc_ready = lndbtc_ready or ("has no active channels" in info["lndMap"][0][1]["status"])
                    lndltc_ready = lndltc_ready or ("has no active channels" in info["lndMap"][1][1]["status"])
                    raiden_ready = raiden_ready or ("has no active channels" in info["raiden"]["status"])
                if lndbtc_ready and lndltc_ready and raiden_ready:
                    return "Ready"
                else:
                    not_ready = []
                    if not lndbtc_ready:
                        not_ready.append("lndbtc")
                    if not lndltc_ready:
                        not_ready.append("lndltc")
                    if not raiden_ready:
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
