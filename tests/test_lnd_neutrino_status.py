from launcher.service.lnd import Lnd
from launcher.service.base import Context
import os

def test_get_logs():
    ctx = Context("mainnet", os.path.expanduser("~/.xud-docker/mainnet"))
    lnd = Lnd(ctx, "lndbtc", "bitcoin")
    lines = lnd._get_logs()
    for line in lines:
        print(line)


def test_filter_logs():
    ctx = Context("mainnet", os.path.expanduser("~/.xud-docker/mainnet"))
    lnd = Lnd(ctx, "lndbtc", "bitcoin")
    lines = lnd._get_logs()
    for line in lines:
        if lnd.PATTERN_NEUTRINO_SYNCING_BEGIN.match(line):
            print(">>> BEGIN <<<", line)
        if lnd.PATTERN_NEUTRINO_SYNCING.match(line):
            print(">>> SYNCING <<<", line)
        if lnd.PATTERN_NEUTRINO_SYNCING_END.match(line):
            print(">>> END <<<", line)


def test_filter_logs_btcn():
    ctx = Context("mainnet", os.path.expanduser("~/.xud-docker/mainnet"))
    lnd = Lnd(ctx, "lndbtc", "bitcoin")
    lines = lnd._get_logs()
    for line in lines:
        if "BTCN" in line:
            print(line)

# 2020-12-21 14:26:44.603 [INF] LTND: Waiting for wallet encryption password. Use `lncli create` to create a wallet, `lncli unlock` to unlock an existing wallet, or `lncli changepassword` to change the password of an existing wallet and unlock it.


def test_get_neutrino_status():
    ctx = Context("mainnet", os.path.expanduser("~/.xud-docker/mainnet"))
    lnd = Lnd(ctx, "lndbtc", "bitcoin")
    text = lnd.get_neutrino_status()
    print(text)


def test_get_current_height():
    ctx = Context("mainnet", os.path.expanduser("~/.xud-docker/mainnet"))
    lnd = Lnd(ctx, "lndbtc", "bitcoin")
    height = lnd.get_current_height()
    print(height)


def test_lnd_status():
    ctx = Context("mainnet", os.path.expanduser("~/.xud-docker/mainnet"))
    lnd = Lnd(ctx, "lndbtc", "bitcoin")
    print(lnd.status)
