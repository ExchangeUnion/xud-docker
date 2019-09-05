#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import shlex
from subprocess import Popen, PIPE
import sys
import argparse
import threading
import signal
import json
import logging

PYTHON2 = (sys.version_info[0] == 2)

if PYTHON2:
    from Queue import Queue, Empty
elif sys.version_info[0] == 3:
    from queue import Queue, Empty

class Service(object):
    def __init__(self, display_name, name):
        self.display_name = display_name
        self.name = name
        self._listeners = []
        self._lock = threading.RLock()
        self._status = None

    def _run(self):
        self._status = get_status(self)
        for listener in self._listeners:
            listener(self, self._status)

    @property
    def status(self):
        if self._status is None:
            if self._lock.acquire(blocking=False):
                t = threading.Thread(target=self._run)
                t.start()
            return "Fetching..."
        return self._status

    def add_status_listener(self, listener):
        self._listeners.append(listener)


networks = {
    "simnet": [
        Service("lndbtc", "lndbtc"),
        Service("ltc", "ltcd"),
        Service("lndltc", "lndltc"),
        Service("raiden", "raiden"),
        Service("xud", "xud"),
    ],

    "testnet": [
        Service("btc", "bitcoind"),
        Service("lndbtc", "lndbtc"),
        Service("ltc", "litecoind"),
        Service("lndltc", "lndltc"),
        Service("parity", "parity"),
        Service("raiden", "raiden"),
        Service("xud", "xud"),
    ],

    "mainnet": [
        Service("btc", "bitcoind"),
        Service("lndbtc", "lndbtc"),
        Service("ltc", "litecoind"),
        Service("lndltc", "lndltc"),
        Service("parity", "parity"),
        Service("raiden", "raiden"),
        Service("xud", "xud"),
    ],
}


class MyException(Exception):
    def __init(self, command, returncode, details):
        super(MyException, self).__init__("Failed to execute: {}".format(command))
        self.command = command
        self.returncode = returncode
        self.details = details


def get_output(command):
    p = Popen(shlex.split(command), stdin=None, stdout=PIPE, stderr=PIPE, shell=False)
    out, err = p.communicate()
    if p.returncode != 0:
        raise MyException(command, p.returncode, err)
    return out.decode().strip()


def get_status_text(blocks, headers):
    if blocks == headers:
        return "Ready"
    else:
        return "Syncing {:.2f}% ({}/{})".format(blocks / headers * 100 - 0.005, blocks, headers)


def get_bitcoind_kind_status(cli):
    cmd = ltcctl + " getblockchaininfo"
    info = json.loads(get_output(cmd))
    blocks = info["blocks"]
    headers = info["headers"]
    return get_status_text(blocks, headers)


def get_lndbtc_status():
    cmd = lndbtc_lncli + " getinfo"
    info = json.loads(get_output(cmd))
    synced_to_chain = info["synced_to_chain"]
    if synced_to_chain:
        return "Ready"
    else:
        return "Waiting for sync"


def get_lndltc_status():
    cmd = lndltc_lncli + " getinfo"
    info = json.loads(get_output(cmd))
    block_height = info["block_height"]
    cmd = ltcctl + " getblockchaininfo"
    info = json.loads(get_output(cmd))
    blocks = info["blocks"]
    return get_status_text(block_height, blocks)


def get_geth_status():
    raise NotImplementedError()


def get_parity_status():
    raise NotImplementedError()


def get_raiden_status():
    raise NotImplementedError()


def get_xud_status():
    raise NotImplementedError()


def get_status(service):
    try:
        name = service.name

        logging.debug("get_status %s", name)

        cmd = "docker-compose ps -q {}".format(name)
        container_id = get_output(cmd)
        if len(container_id) == 0:
            return "Container not exist"

        cmd = "docker inspect -f '{{.State.Running}}' " + container_id
        running = get_output(cmd)
        if running == "false":
            return "Container down"

        if name == "bitcoind":
            return get_bitcoind_kind_status(bitcoin_cli)
        elif name == "btcd":
            return get_bitcoind_kind_status(btcctl)
        elif name == "litecoind":
            return get_bitcoind_kind_status(litecoin_cli)
        elif name == "ltcd":
            return get_bitcoind_kind_status(ltcctl)
        elif name == "lndbtc":
            return get_lndbtc_status()
        elif name == "lndltc":
            return get_lndltc_status()
        elif name == "geth":
            return get_geth_status()
        elif name == "parity":
            return get_parity_status()
        elif name == "raiden":
            return get_raiden_status()
        elif name == "xud":
            return get_xud_status()
        else:
            return ""
    except MyException as e:
        return "ERROR: [{}] {}".format(e.command, e.details)


def pretty_print_statuses(services):
    q = Queue()

    def on_change(service, status):
        q.put((service, status))

    for service in services:
        service.add_status_listener(on_change)

    padding = 2
    headers = ["SERVICE", "STATUS"]
    w1 = max([len(s.display_name) for s in services] +
             [len(headers[0])]) + padding * 2

    w2 = max([len(s.status) for s in services] +
             [len(headers[1]), 40]) + padding * 2

    # os.system("tput civis")  # hide cursor
    # os.system("stty -echo")

    # sys.stdout.write("\033[6n")  # show cursor position

    def f(text, width, padding):
        return (" " * padding) + text + (" " * (width - padding - len(text)))

    print("┏{}┯{}┓".format(("━" * w1), ("━" * w2)))
    print("┃{}│{}┃".format(
        f(headers[0], w1, padding),
        f(headers[1], w2, padding),
    ))
    for s in services:
        print("┠{}┼{}┨".format(("─" * w1), ("─" * w2)))
        print("┃{}│{}┃".format(
            f(s.display_name, w1, padding),
            f(s.status, w2, padding),
        ))
    print("┗{}┷{}┛".format(("━" * w1), ("━" * w2)))

    while True:
        logging.debug("waiting queue")

        if PYTHON2:
            try:
                service, status = q.get(timeout=1)
            except Empty:
                continue
        else:
            service, status = q.get(block=True)

        logging.debug("get: %s, %s", service.name, status)

        n = 0
        for i, s in enumerate(services):
            if s.name == service.name:
                n = (len(services) - i) * 2
                break

        s1 = "\033[{}A".format(n)
        s2 = "\033[{}B".format(n)
        content_format = "{{:{}s}}".format(w2 - padding * 2)
        status = "{}".format(status)
        content = content_format.format(status)
        update = "{}\033[15C{}\033[{}D{}".format(s1, content, 15 + len(content), s2)
        print(update, end="")
        sys.stdout.flush()


def get_all_services():
    services = []
    for service in networks[network]:
        services.append(service)
    return services


def show_status():
    shutdown_event = threading.Event()
    try:
        services = get_all_services(shutdown_event)
        pretty_print_statuses(services)
    except KeyboardInterrupt:
        logging.debug("Ctrl-C detected")
        # os.system("stty echo")
        # os.system("tput cnorm")  # show cursor
        shutdown_event.set()
        # TODO clear stdin buffer
        exit(1)


def get_active_channels_count(result):
    try:
        return len([c for c in result["channels"] if c["active"]])
    except:
        return 0


def check_channel(stop_event, chain):
    if chain == "bitcoin":
        service = "lndbtc"
    elif chain == "litecoin":
        service = "lndltc"
    else:
        raise Exception("Unsupported chain: %s" % chain)

    lncli = "docker-compose exec {} lncli -n {} -c {}".format(service, network, chain)
    cmd = "{} listchannels".format(lncli)

    p = None  # type: Popen or None

    while not stop_event.is_set():
        p = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE, shell=False)
        out, err = p.communicate()
        if p.returncode == 0:
            result = json.loads(out.decode().strip())
            if get_active_channels_count(result) > 0:
                break
        stop_event.wait(3)  # sleep 3

    try:
        p.send_signal(signal.SIGINT)
    except:
        pass


def print_dots(stop_event):
    while not stop_event.is_set():
        print(".", end="")
        sys.stdout.flush()
        stop_event.wait(1)
    print()


def launch_check():
    if network == "simnet":
        print("Waiting for LND channels to be active")

        stop1 = threading.Event()
        stop2 = threading.Event()
        stop3 = threading.Event()
        t1 = threading.Thread(target=check_channel, args=(stop1, "bitcoin"))
        t2 = threading.Thread(target=check_channel, args=(stop2, "litecoin"))
        t3 = threading.Thread(target=print_dots, args=(stop3,))
        t1.start()
        #t2.start()  # When t1 t2 start at the same time it will break the bash prompt! WTF???
        t3.start()

        t1.join()
        t2.start()
        t2.join()

        stop3.set()
        t3.join()


###############################################################################


network = None
home = None

try:
    home = os.environ["XUD_DOCKER_HOME"]
except KeyError:
    print("Missing environment variable XUD_DOCKER_HOME", file=sys.stderr)
    exit(1)

try:
    network = os.environ["XUD_NETWORK"]
except KeyError:
    print("Missing environment variable XUD_NETWORK", file=sys.stderr)
    exit(1)

bitcoin_cli = "docker-compose exec bitcoind bitcoin-cli -{} -rpcuser=xu -rpcpassword=xu".format(network)
litecoin_cli = "docker-compose exec -T litecoind litecoin-cli -{} -rpcuser=xu -rpcpassword=xu".format(network)
ltcctl = "docker-compose exec ltcd ltcctl --{} --rpcuser=xu --rpcpass=xu".format(network)
btcctl = "docker-compose exec btcd btcctl --{} --rpcuser=xu --rpcpass=xu".format(network)
lndbtc_lncli = "docker-compose exec lndbtc lncli -n {} -c bitcoin".format(network)
lndltc_lncli = "docker-compose exec lndltc lncli -n {} -c litecoin".format(network)
geth = "docker-compose exec geth geth --{}".format(network)
parity = "docker-compose exec parity parity --chain ropsten"
xud = "docker-compose exec xud xucli"

os.chdir(os.path.expanduser(home + "/" + network))
LOG_TIME = '%(asctime)s.%(msecs)03d'
LOG_LEVEL = '%(levelname)5s'
LOG_PID = '%(process)d'
LOG_THREAD = '[%(threadName)15s]'
LOG_LOGGER = '%(name)10s'
LOG_MESSAGE = '%(message)s'
LOG_FORMAT = '%s %s %s --- %s %s: %s' % (LOG_TIME, LOG_LEVEL, LOG_PID, LOG_THREAD, LOG_LOGGER, LOG_MESSAGE)
logging.basicConfig(filename="xud-docker.log", filemode="w", format=LOG_FORMAT, level=logging.DEBUG)

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest="command")
status = subparsers.add_parser("status")
check = subparsers.add_parser("check")

args = parser.parse_args()
if args.command == "status":
    show_status()
elif args.command == "check":
    launch_check()
