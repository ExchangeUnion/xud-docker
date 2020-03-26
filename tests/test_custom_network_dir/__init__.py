import os
from shutil import copyfile
import pexpect
import time
from subprocess import check_output, CalledProcessError, PIPE


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


def expect_multilines(child, content):
    pass


def create_wallet(child, retry=0):
    if retry == 0:
        print("[EXPECT] Create/Restore choice")
        try:
            child.expect("Do you want to create a new xud environment or restore an existing one?", timeout=60)
            print(child.before, end="")
            print(child.match.group(0))

            child.expect("Please choose: ")
            print(child.before, end="")
            print(child.match.group(0))

            child.sendline("1\r")
        except pexpect.exceptions.EOF:
            print("Error: Exits unexpectedly")
            print(child.before)
            exit(1)
        except pexpect.exceptions.TIMEOUT:
            print("Error: Timeout")
            print(child.before)
            exit(1)

    print("[EXPECT] Xud master password")
    try:
        child.expect("You are creating an xud node key and underlying wallets.", timeout=180)
        print(child.before, end="")
        print(child.match.group(0))

        child.expect("Enter a password: ")
        print(child.before, end="")
        print(child.match.group(0))
        child.sendline("12345678\r")

        child.expect("Re-enter password: ")
        print(child.before, end="")
        print(child.match.group(0))
        child.sendline("12345678\r")

        i = child.expect([
            "----------------------BEGIN XUD SEED---------------------",
            "Please choose: "
        ])
        print(child.before, end="")
        print(child.match.group(0))

        if i == 0:
            child.expect("-----------------------END XUD SEED----------------------")
            seed = child.before
            print(seed)
        elif i == 1:
            child.sendline("1\r")
            print("Wait 5 seconds")
            time.sleep(5)
            create_wallet(child, retry=retry + 1)
            return

        child.expect("YOU WILL NOT BE ABLE TO DISPLAY YOUR XUD SEED AGAIN. Press ENTER to continue...")
        print(child.before, end="")
        print(child.match.group(0))
        child.sendline("\r")
    except pexpect.exceptions.EOF:
        print("Error: Exits unexpectedly")
        print(child.before)
        exit(1)
    except pexpect.exceptions.TIMEOUT:
        print("Error: Timeout")
        print(child.before)
        exit(1)


def test():
    cleanup()

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

    child = pexpect.spawnu("bash setup.sh -b fix/geth-mode --nodes-json ./nodes.json")

    print("[EXPECT] Network choosing (testnet)")
    try:
        child.expect("Please choose the network: ")
        print(child.before, end="")
        print(child.match.group(0))
        child.sendline("2")
    except pexpect.exceptions.EOF:
        print("Error: Exits unexpectedly")
        print(child.before)
        exit(1)
    except pexpect.exceptions.TIMEOUT:
        print("Error: Timeout")
        print(child.before)
        exit(1)

    print("[EXPECT] Launching testnet environment")
    try:
        child.expect("🚀 Launching testnet environment", timeout=90)
        print(child.before, end="")
        print(child.match.group(0))
    except pexpect.exceptions.EOF:
        print("Error: Exits unexpectedly")
        print(child.before)
        exit(1)
    except pexpect.exceptions.TIMEOUT:
        print("Error: Timeout")
        print(child.before)
        exit(1)

    print("[EXPECT] Checking for updates")
    try:
        child.expect("🌍 Checking for updates...")
        print(child.before, end="")
        print(child.match.group(0))
    except pexpect.exceptions.EOF:
        print("Error: Exits unexpectedly")
        print(child.before)
        exit(1)
    except pexpect.exceptions.TIMEOUT:
        print("Error: Timeout")
        print(child.before)
        exit(1)

    create_wallet(child)

    print("[EXPECT] Backup location setup")
    try:
        child.expect("Enter path to backup location: ")
        print(child.before, end="")
        print(child.match.group(0))
        child.sendline("/tmp/xud-testnet-backup\r")

        child.expect("Checking backup location...")
        print(child.before, end="")
        print(child.match.group(0))

    except pexpect.exceptions.EOF:
        print("Error: Exits unexpectedly")
        print(child.before)
        exit(1)
    except pexpect.exceptions.TIMEOUT:
        print("Error: Timeout")
        print(child.before)
        exit(1)

    print("[Expect] Xudctl shell")
    try:
        child.expect("testnet > ")
        print(child.before, end="")
        print(child.match.group(0))
        child.sendline("status\r")

        child.expect("testnet > ")
        print(child.before, end="")
        print(child.match.group(0))
        child.sendline("exit\r")

        child.eof()

    except pexpect.exceptions.EOF:
        print("Error: Exits unexpectedly")
        print(child.before)
        exit(1)
    except pexpect.exceptions.TIMEOUT:
        print("Error: Timeout")
        print(child.before)
        exit(1)
