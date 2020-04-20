import pytest
import pexpect
import docker
import docker.errors
import time
import os
from shutil import copyfile
from subprocess import check_output, PIPE, CalledProcessError
import sys
import re
import json

from .utils import simulate_tty


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
        return target

    utils = find("utils")

    if utils:
        exit_code, output = utils.exec_run("cat /var/log/launcher.log")
        print(output.decode())

    # exit_code, output = find("xud").exec_run("xucli --rpcport=18886 getinfo")
    # print(output.decode())
    # os.system("docker exec testnet_xud_1 bash -c 'netstat -ant | grep LISTEN'")
    # os.system("docker exec testnet_xud_1 cat /root/.xud/xud.conf")
    # os.system("docker exec testnet_xud_1 cat /app/entrypoint.sh")
    #
    # print("Raiden logs:")
    # print(find("raiden").logs().decode())

    print("-" * 80)


def expect_banner(child):
    print("[EXPECT] The banner")
    banner = open(os.path.dirname(__file__) + "/banner.txt").read()
    banner = banner.replace("\n", "\r\n")
    child.expect_exact(banner, timeout=500)
    lines = simulate_tty(child.before)
    for line in lines:
        print(line)
    print(child.match, end="")


def wait_lnd_synced(chain):
    if chain == "bitcoin":
        name = "lndbtc"
    elif chain == "litecoin":
        name = "lndltc"
    else:
        raise ValueError("chain should be bitcoin or litecoin")

    height = None
    for i in range(100):
        try:
            info = json.loads(check_output("docker exec simnet_{}_1 lncli -n simnet -c {} getinfo".format(name, chain), shell=True, stderr=PIPE).decode())
            height = info["block_height"]
        except CalledProcessError as e:
            print(e.stderr.decode())
        time.sleep(3)

    if not height:
        raise AssertionError("Failed to get block height of {}".format(name))

    print("{} block height: {}".format(name, height))

    for i in range(100000):
        try:
            lines = check_output("docker logs --tail=100 simnet_{}_1 | grep 'New block'".format(name), shell=True, stderr=PIPE).decode().splitlines()
            if len(lines) > 0:
                p = re.compile(r"^.*height=(\d+).*$")
                m = p.match(lines[-1])
                if m:
                    current_height = int(m.group(1))
                    print("{} current block height: {}/{}".format(name, current_height, height))
                    if current_height >= height:
                        return
                else:
                    print(lines[-1])
        except CalledProcessError as e:
            print(e.stderr.decode())
        time.sleep(3)
    raise AssertionError("Failed to wait for {}".format(name))


def expect_command_status(child):
    wait_lnd_synced("bitcoin")
    wait_lnd_synced("litecoin")

    print(child.before, end="")
    print(child.match.group(0), end="")
    sys.stdout.flush()

    child.sendline("status\r")
    child.expect("status\r\n")
    print("status")

    child.expect("simnet > ")

    lines = simulate_tty(child.before)
    for line in lines:
        print(line)

    nodes = ["lndbtc", "lndltc", "raiden", "xud"]

    status = {}

    for i, node in enumerate(nodes):
        p = re.compile(r"^.*%s.*│(.+)│.*$" % node)
        m = p.match(lines[i * 2 + 3])
        if m:
            status[node] = m.group(1).strip()
        else:
            raise AssertionError("Failed to parse {} status".format(node))

    print(status)

    print(child.match.group(0), end="")
    sys.stdout.flush()


def expect_command_getinfo(child):
    child.sendline("getinfo\r")
    child.expect("getinfo\r\n")
    print("getinfo")

    child.expect("simnet > ")
    for line in simulate_tty(child.before):
        print(line)
    print(child.match.group(0), end="")
    sys.stdout.flush()


def expect_command_exit(child):
    child.sendline("exit\r")
    child.expect("exit\r\n")
    print("exit")

    child.eof()


def simple_flow(child):
    print("[EXPECT] Network choosing (simnet)")
    child.expect("Please choose the network: ")
    print(child.before, end="")
    print(child.match.group(0), end="")
    sys.stdout.flush()

    child.sendline("1")
    child.expect("1\r\n")
    print("1")

    print("[EXPECT] Launching simnet environment")
    child.expect("🚀 Launching simnet environment\r\n", timeout=90)
    print(child.before, end="")
    print(child.match.group(0), end="")
    sys.stdout.flush()

    print("[EXPECT] Checking for updates")
    child.expect("🌍 Checking for updates...\r\n")
    print(child.before, end="")
    print(child.match.group(0), end="")
    sys.stdout.flush()

    expect_banner(child)

    child.expect("simnet > ")

    expect_command_status(child)
    expect_command_getinfo(child)
    expect_command_exit(child)


def run_flow(child, flow):
    try:
        flow(child)
    except pexpect.exceptions.EOF:
        raise AssertionError("The program exits unexpectedly: {}".format(child.before.strip()))
    except pexpect.exceptions.TIMEOUT:
        raise AssertionError("Timeout")
    except KeyboardInterrupt:
        raise AssertionError("Interrupted")


def diagnose():
    check_containers()


@pytest.mark.integration_test
def test1():
    print()  # avoid output first line being in the end of pytest case line
    cleanup()
    try:
        output = check_output("git rev-parse --abbrev-ref HEAD", shell=True)
        branch = output.decode().splitlines()[0]
        if branch == "HEAD":
            branch = os.environ["TRAVIS_BRANCH"]
        cmd = "bash setup.sh -b {}".format(branch)
        print("$ {}".format(cmd))
        child = pexpect.spawnu(cmd)
        run_flow(child, simple_flow)
    except:
        diagnose()
        raise
    finally:
        cleanup()
