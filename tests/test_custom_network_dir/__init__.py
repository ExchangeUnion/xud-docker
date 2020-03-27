import os
import sys
import time
from shutil import copyfile
from subprocess import check_output, CalledProcessError, PIPE
import pexpect


def cleanup_images(network):
    print("[CLEANUP] {} images".format(network))


def cleanup_containers(network):
    print("[CLEANUP] {} containers".format(network))
    containers = []
    try:
        containers = check_output("docker ps --filter name={} -q -a".format(network), shell=True, stderr=PIPE).decode().splitlines()
    except CalledProcessError:
        pass

    if len(containers) > 0:
        try:
            cmd = "docker stop {}".format(" ".join(containers))
            print(cmd)
            check_output(cmd, shell=True, stderr=PIPE).decode().splitlines()
        except CalledProcessError:
            pass

        try:
            cmd = "docker rm {}".format(" ".join(containers))
            print(cmd)
            check_output(cmd, shell=True, stderr=PIPE).decode().splitlines()
        except CalledProcessError:
            pass

    cleanup_images(network)


def cleanup():
    cleanup_containers("simnet")
    cleanup_containers("testnet")
    cleanup_containers("mainnet")
    print("[CLEANUP] Removing ~/.xud-docker")
    os.system("sudo rm -rf ~/.xud-docker")
    print("[CLEANUP] Removing /tmp/xud-testnet")
    os.system("sudo rm -rf /tmp/xud-testnet")
    print("[CLEANUP] Removing /tmp/xud-testnet-backup")
    os.system("sudo rm -rf /tmp/xud-testnet-backup")


class TestFailure(Exception):
    pass


def create_wallet(child, retry=0):
    if retry > 10:
        raise TestFailure("Wallets creating failed too many times")
    if retry == 0:
        print("[EXPECT] Create/Restore choice")
        child.expect("Do you want to create a new xud environment or restore an existing one\?", timeout=60)
        print(child.before, end="")
        print(child.match.group(0), end="")
        sys.stdout.flush()

        child.expect("Please choose: ")
        print(child.before, end="")
        print(child.match.group(0), end="")
        sys.stdout.flush()

        child.sendline("1\r")
        child.expect("1\r\n")
        print("1")

    print("[EXPECT] Xud master password")
    child.expect("You are creating an xud node key and underlying wallets.", timeout=180)
    print(child.before, end="")
    print(child.match.group(0), end="")
    sys.stdout.flush()

    child.expect("Enter a password: ")
    print(child.before, end="")
    print(child.match.group(0), end="")
    sys.stdout.flush()
    child.sendline("12345678\r")
    child.expect("\r\n")
    print()

    child.expect("Re-enter password: ")
    print(child.before, end="")
    print(child.match.group(0), end="")
    sys.stdout.flush()
    child.sendline("12345678\r")
    child.expect("\r\n")
    print()

    i = child.expect([
        "----------------------BEGIN XUD SEED---------------------",
        "Please choose: "
    ])
    print(child.before, end="")
    print(child.match.group(0), end="")
    sys.stdout.flush()

    if i == 0:
        child.expect("-----------------------END XUD SEED----------------------")
        seed = child.before
        print(child.before, end="")
        print(child.match.group(0), end="")
        sys.stdout.flush()
    elif i == 1:
        child.sendline("1\r")
        child.expect("1\r\n")
        print("1")
        print("[RETRY] Creating wallets in 5 seconds")
        time.sleep(5)
        create_wallet(child, retry=retry + 1)
        return

    child.expect("YOU WILL NOT BE ABLE TO DISPLAY YOUR XUD SEED AGAIN. Press ENTER to continue...")
    print(child.before, end="")
    print(child.match.group(0), end="")
    child.sendline("\r")
    child.expect("\r\n")
    print()


def prepare():
    backup_dir = "/tmp/xud-testnet-backup"
    os.mkdir(backup_dir)

    home_dir = os.path.expanduser("~/.xud-docker/")
    os.mkdir(home_dir)
    copyfile(os.path.dirname(__file__) + "/xud-docker.conf", home_dir + "/xud-docker.conf")

    network_dir = "/tmp/xud-testnet"
    os.mkdir(network_dir)
    copyfile(os.path.dirname(__file__) + "/testnet.conf", network_dir + "/testnet.conf")

    os.system("sed -i.bak 's/<id>/{}/' {}".format(os.environ["INFURA_PROJECT_ID"], network_dir + "/testnet.conf"))
    os.system("sed -i.bak 's/<secret>/{}/' {}".format(os.environ["INFURA_PROJECT_SECRET"], network_dir + "/testnet.conf"))


def simple_flow(child):
    print("[EXPECT] Network choosing (testnet)")
    child.expect("Please choose the network: ")
    print(child.before, end="")
    print(child.match.group(0), end="")
    sys.stdout.flush()

    child.sendline("2")
    child.expect("2\r\n")
    print("2")

    print("[EXPECT] Launching testnet environment")
    child.expect("🚀 Launching testnet environment\r\n", timeout=90)
    print(child.before, end="")
    print(child.match.group(0), end="")
    sys.stdout.flush()

    print("[EXPECT] Checking for updates")
    child.expect("🌍 Checking for updates...\r\n")
    print(child.before, end="")
    print(child.match.group(0), end="")
    sys.stdout.flush()

    create_wallet(child)

    print("[EXPECT] Backup location setup")
    child.expect("Enter path to backup location: ")
    print(child.before, end="")
    print(child.match.group(0), end="")
    sys.stdout.flush()
    child.sendline("/tmp/xud-testnet-backup\r")
    child.expect("/tmp/xud-testnet-backup\r\n")
    print("/tmp/xud-testnet-backup")

    child.expect("Checking backup location... (.*).")
    print(child.before, end="")
    print(child.match.group(0), end="")
    sys.stdout.flush()

    print("[EXPECT] Xudctl shell")
    child.expect("testnet > ")
    print(child.before, end="")
    print(child.match.group(0), end="")
    sys.stdout.flush()

    child.sendline("status\r")
    child.expect("status\r\n")
    print("status")

    child.expect("testnet > ")
    print(child.before, end="")
    print(child.match.group(0), end="")
    sys.stdout.flush()

    child.sendline("exit\r")
    child.expect("exit\r\n")
    print("exit")

    child.eof()


def test1(branch):
    try:
        prepare()
        opts = [
            "--testnet-dir=/tmp/xud-testnet",
            "--bitcoind.mode=neutrino",
            "--litecoind.mode=neutrino",
            "--geth.mode=infura",
        ]
        child = pexpect.spawnu("bash setup.sh -b {} --nodes-json ./nodes.json {}".format(branch, " ".join(opts)))
        try:
            simple_flow(child)
            print("-" * 80)
            print(":: TEST #1 PASSED!")
            print("-" * 80)
        except pexpect.exceptions.EOF:
            print("Error: Exits unexpectedly")
            print(child.before)
            exit(1)
        except pexpect.exceptions.TIMEOUT:
            print("Error: Timeout")
            print(child.before)
            exit(1)
        except KeyboardInterrupt:
            pass
            exit(1)
        except TestFailure as e:
            print("Eorrr: {}".format(e))
            exit(1)
    finally:
        cleanup()


def test2(branch):
    try:
        prepare()
        child = pexpect.spawnu("bash setup.sh -b {} --nodes-json ./nodes.json".format(branch))
        try:
            simple_flow(child)
            print("-" * 80)
            print(":: TEST #2 PASSED!")
            print("-" * 80)
        except pexpect.exceptions.EOF:
            print("Error: Exits unexpectedly")
            print(child.before)
            exit(1)
        except pexpect.exceptions.TIMEOUT:
            print("Error: Timeout")
            print(child.before)
            exit(1)
        except KeyboardInterrupt:
            pass
            exit(1)
        except TestFailure as e:
            print("Error: {}".format(e))
            exit(1)
    finally:
        cleanup()


def test(branch):
    cleanup()
    test1(branch)
    test2(branch)
