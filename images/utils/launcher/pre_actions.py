from .node import Node, PasswordNotMatch, MnemonicNot24Words, InvalidPassword, LndApiError, XudApiError

def _no_lnd_wallet(self, lnd):
    while True:
        try:
            info = lnd.api.getinfo()
            break
        except LndApiError as e:
            if "unable to read macaroon path" in str(e):
                return True
            elif "open /root/.lnd/tls.cert: no such file or directory" in str(e):
                continue
            elif "Wallet is encrypted" in str(e):
                return False
        time.sleep(3)
    return False


def _pristine(self):
    lndbtc = self._get_node("lndbtc")
    lndltc = self._get_node("lndltc")
    return self._no_lnd_wallet(lndbtc) or self._no_lnd_wallet(lndltc)


def _ensure_xud(self):
    xud = self._get_node("xud")
    while True:
        try:
            xud.api.getinfo()
        except XudApiError as e:
            if "UNIMPLEMENTED" in str(e) or "xud is locked" in str(e):
                break
        time.sleep(3)


def _check_wallets(self):
    if self._pristine():
        self._ensure_xud()

        while True:
            print("Would you like to create a new xud node or restore an existing one?")
            print("1) New")
            print("2) Restore")
            reply = input("Please choose: ")
            if reply == "1":
                self.xucli_restore_wrapper(xud)
            elif reply == "2":
                self.xucli_create_wrapper(xud)


def _wait_channels(self):
    # TODO wait for channels
    pass


def _get_commands(self):
    pass


def _confirm(self, prompt):
    pass


def xucli_create_wrapper(self, xud):
    counter = 0
    ok = False
    while counter < 3:
        try:
            xud.cli("create", self._shell)
            while True:
                confirmed = self._confirm("YOU WILL NOT BE ABLE TO DISPLAY YOUR XUD SEED AGAIN. Press ENTER to continue...")
                if confirmed:
                    break
            ok = True
            break
        except (PasswordNotMatch, InvalidPassword):
            counter += 1
            continue
    if not ok:
        raise Exception("Failed to create wallets")


def xucli_restore_wrapper(self, xud):
    counter = 0
    ok = False
    while counter < 3:
        try:
            command = "restore"
            if self._config.backup_dir:
                command += " /root/.xud-backup"
            xud.cli(command, self._shell)
            ok = True
            break
        except (PasswordNotMatch, InvalidPassword, MnemonicNot24Words):
            counter += 1
            continue
    if not ok:
        raise Exception("Failed to restore wallets")


def run():
    if self.network in ["testnet", "mainnet"]:
        self._check_wallets()
    elif self.network == "simnet":
        self._wait_channels()