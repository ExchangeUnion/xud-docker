import time
from .node import Node, PasswordNotMatch, MnemonicNot24Words, InvalidPassword, LndApiError, XudApiError
from .context import DockerContext

def _no_lnd_wallet(lnd):
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


def _pristine(context: DockerContext):
    lndbtc = context.get_node("lndbtc")
    lndltc = context.get_node("lndltc")
    return _no_lnd_wallet(lndbtc) or _no_lnd_wallet(lndltc)


def _ensure_xud(context: DockerContext):
    xud = context.get_node("xud")
    while True:
        try:
            xud.api.getinfo()
        except XudApiError as e:
            if "UNIMPLEMENTED" in str(e) or "xud is locked" in str(e):
                break
        time.sleep(3)


def _check_wallets(context: DockerContext):
    if _pristine(context):
        _ensure_xud(context)

        xud = context.get_node("xud")

        while True:
            print("Would you like to create a new xud node or restore an existing one?")
            print("1) New")
            print("2) Restore")
            reply = input("Please choose: ")
            if reply == "1":
                xucli_restore_wrapper(xud, context.config.backup_dir)
            elif reply == "2":
                xucli_create_wrapper(xud)


def _wait_channels(self):
    # TODO wait for channels
    pass


def _confirm(prompt):
    reply = input(prompt)
    return reply == ""


def xucli_create_wrapper(xud):
    counter = 0
    ok = False
    while counter < 3:
        try:
            xud.cli("create")
            while True:
                confirmed = _confirm("YOU WILL NOT BE ABLE TO DISPLAY YOUR XUD SEED AGAIN. Press ENTER to continue...")
                if confirmed:
                    break
            ok = True
            break
        except (PasswordNotMatch, InvalidPassword):
            counter += 1
            continue
    if not ok:
        raise Exception("Failed to create wallets")


def xucli_restore_wrapper(xud, backup_dir):
    counter = 0
    ok = False
    while counter < 3:
        try:
            command = "restore"
            if backup_dir:
                command += " /root/.xud-backup"
            xud.cli(command)
            ok = True
            break
        except (PasswordNotMatch, InvalidPassword, MnemonicNot24Words):
            counter += 1
            continue
    if not ok:
        raise Exception("Failed to restore wallets")


def run(context: DockerContext):
    network = context.network
    if network in ["testnet", "mainnet"]:
        _check_wallets(context)
    elif network == "simnet":
        _wait_channels(context)
