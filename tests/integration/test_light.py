import pytest
import pexpect
import docker
import docker.errors
import time
import os
from shutil import copyfile
from subprocess import check_output, CalledProcessError, PIPE
import sys


def cleanup_containers(network):
    client = docker.from_env()

    containers = client.containers.list(all=True, filters={
        "name": "{}_".format(network)
    })

    if len(containers) > 0:
        print("[CLEANUP] {} containers".format(network))
        for c in containers:
            print("- {}".format(c.attrs["Name"]))
            try:
                c.stop()
            except:
                pass
            try:
                c.remove()
            except:
                pass


    # cleanup_images(network)

    try:
        name = "{}_default".format(network)
        network = client.networks.get(name)
        print("[CLEANUP] network: {}".format(name))
        network.remove()
    except docker.errors.NotFound:
        pass


def cleanup_dir(file):
    if os.path.exists(file):
        print("[CLEANUP] Removing {}".format(file))
        os.system("sudo rm -rf {}".format(file))


def cleanup():
    cleanup_containers("simnet")
    cleanup_containers("testnet")
    cleanup_containers("mainnet")
    cleanup_dir(os.path.expanduser("~/.xud-docker"))
    cleanup_dir(os.path.expanduser("/tmp/xud-testnet"))
    cleanup_dir(os.path.expanduser("/tmp/xud-testnet-backup"))


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


def check_containers():
    client = docker.from_env()
    containers = client.containers.list(filters={
        "name": "testnet_"
    })
    print("-" * 80)
    print("Running containers:")
    for c in containers:
        print("- {}".format(c.attrs["Name"]))

    def find(name):
        target = None
        for c in containers:
            if name in c.attrs["Name"]:
                target = c
                break
        if not target:
            raise AssertionError("Container not found: {}".format(name))
        return target

    exit_code, output = find("utils").exec_run("cat /var/log/launcher.log")
    print(output.decode())

    # exit_code, output = find("xud").exec_run("xucli --rpcport=18886 getinfo")
    # print(output.decode())
    #
    # print("Raiden logs:")
    # print(find("raiden").logs().decode())

    print("-" * 80)


def create_wallet(child, retry=0):
    if retry > 10:
        raise AssertionError("Creating wallets failed too many times")
    if retry == 0:
        print("[EXPECT] Create/Restore choice")
        child.expect(r"Do you want to create a new xud environment or restore an existing one\?", timeout=500)
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
        "----------------------BEGIN XUD SEED---------------------\r\n",
        r"Do you want to create a new xud environment or restore an existing one\?\r\n",
    ])

    if i == 0:
        print(child.before, end="")
        print(child.match.group(0), end="")
        sys.stdout.flush()

        child.expect("-----------------------END XUD SEED----------------------\r\n")
        seed = child.before
        print(child.before, end="")
        print(child.match.group(0), end="")
        sys.stdout.flush()
    elif i == 1:
        failed_reason = child.before
        failed_reason = failed_reason.strip()
        print(child.before, end="")
        sys.stdout.flush()

        if failed_reason == "xud is starting... try again in a few seconds":
            pass
        elif failed_reason == "Error: 13 INTERNAL: could not initialize lnd-BTC: 14 UNAVAILABLE: failed to connect to all addresses":
            pass
        elif failed_reason == "Error: 13 INTERNAL: could not initialize lnd-LTC: 14 UNAVAILABLE: failed to connect to all addresses":
            pass
        elif failed_reason == "Error: 14 UNAVAILABLE: lnd-BTC is Disconnected":
            pass
        elif failed_reason == "Error: 14 UNAVAILABLE: lnd-LTC is Disconnected":
            pass
        else:
            raise AssertionError("Failed to create wallets: {}".format(failed_reason))

        print(child.match.group(0), end="")
        sys.stdout.flush()

        child.expect("Please choose: ")
        print(child.before, end="")
        print(child.match.group(0), end="")
        sys.stdout.flush()

        time.sleep(5)

        child.sendline("1\r")
        child.expect("1\r\n")
        print("1")
        create_wallet(child, retry=retry + 1)
        return

    child.expect("YOU WILL NOT BE ABLE TO DISPLAY YOUR XUD SEED AGAIN. Press ENTER to continue...")
    print(child.before, end="")
    print(child.match.group(0), end="")
    child.sendline("\r")
    child.expect("\r\n")
    print()


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

    child.sendline("getinfo\r")
    child.expect("getinfo\r\n")
    print("getinfo")

    child.expect("testnet > ")
    print(child.before, end="")
    print(child.match.group(0), end="")
    sys.stdout.flush()

    child.sendline("exit\r")
    child.expect("exit\r\n")
    print("exit")

    child.eof()


def run_flow(child, flow):
    try:
        flow(child)
    except pexpect.exceptions.EOF:
        raise AssertionError("The program exits unexpectedly")
    except pexpect.exceptions.TIMEOUT:
        raise AssertionError("Timeout")
    except KeyboardInterrupt:
        raise AssertionError("Interrupted")


def diagnose():
    os.system("docker exec testnet_xud_1 bash -c 'netstat -ant | grep LISTEN'")
    os.system("docker exec testnet_xud_1 cat /root/.xud/xud.conf")
    os.system("docker exec testnet_xud_1 cat /app/entrypoint.sh")
    check_containers()


@pytest.mark.integration_test
def test_config_file():
    print()
    cleanup()
    try:
        prepare()
        output = check_output("git rev-parse --abbrev-ref HEAD", shell=True)
        branch = output.decode().splitlines()[0]
        child = pexpect.spawnu("bash setup.sh -b {} --nodes-json ./nodes.json".format(branch))
        run_flow(child, simple_flow)
    except:
        diagnose()
        raise
    finally:
        cleanup()

@pytest.mark.integration_test
def test_command_line_options():
    pass
