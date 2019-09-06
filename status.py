# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
import json
import logging
import os
import shlex
import signal
import sys
import threading
from subprocess import Popen, PIPE
import time
import re

try:
    from queue import Queue
except ImportError:
    from Queue import Queue

try:
    from urllib.request import urlopen, HTTPError
except ImportError:
    from urllib2 import urlopen, HTTPError

PYTHON2 = (sys.version_info[0] == 2)


class Service(object):
    def __init__(self, display_name, name):
        # type: (str, str) -> None
        self.display_name = display_name
        self.name = name

    def start_status_query_thread(self, stop_event, queue):
        # type: (threading.Event, Queue) -> threading.Thread
        def run():
            while not stop_event.is_set():
                status = get_status(self, stop_event)
                queue.put((self, status))
                # stop_event.wait(5)
                break
            logging.debug("stop")

        t = threading.Thread(target=run)
        queue.put((self, "Fetching..."))
        t.start()
        return t


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
        Service("geth", "geth"),
        Service("raiden", "raiden"),
        Service("xud", "xud"),
    ],

    "mainnet": [
        Service("btc", "bitcoind"),
        Service("lndbtc", "lndbtc"),
        Service("ltc", "litecoind"),
        Service("lndltc", "lndltc"),
        Service("geth", "geth"),
        Service("raiden", "raiden"),
        Service("xud", "xud"),
    ],
}


class InvocationException(Exception):
    def __init__(self, command, returncode, details):
        super(InvocationException, self).__init__("Failed to execute: {}".format(command))
        self.command = command
        self.returncode = returncode
        self.details = details

    def __repr__(self):
        return "\n%s\nexit code = %s\n%s\n" % (self.command, self.returncode, self.details)


def get_output(command):
    p = Popen(command, stdin=None, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = p.communicate()
    if p.returncode != 0:
        raise InvocationException(command, p.returncode, err.decode().strip())
    return out.decode().strip()


def get_status_text(blocks, headers):
    if blocks == headers:
        return "Ready"
    else:
        return "Syncing {:.2f}% ({}/{})".format(blocks / headers * 100 - 0.005, blocks, headers)


def get_bitcoind_kind_status(cli):
    # type: (str) -> str
    cmd = cli + " getblockchaininfo"
    info = json.loads(get_output(cmd))
    blocks = info["blocks"]
    headers = info["headers"]
    return get_status_text(blocks, headers)


def get_lnd_kind_status(cli):
    # type: (str) -> str
    cmd = cli + " getinfo"
    info = json.loads(get_output(cmd))
    synced_to_chain = info["synced_to_chain"]
    if synced_to_chain:
        return "Ready"
    else:
        return "Waiting for sync"


def remove_ansi_escape_sequence(s):
    # type: (str) -> str
    ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
    return ansi_escape.sub('', s)


def get_geth_status(cli):
    # type: (str) -> str
    cmd = cli + " --exec 'eth.syncing' attach"
    syncing = remove_ansi_escape_sequence(get_output(cmd))
    logging.debug("syncing is %s", syncing)
    if syncing != 'false':
        j = json.loads(syncing)
        return get_status_text(j["currentBlock"], j["highestBlock"])
    else:
        cmd = cli + " --exec 'eth.blockNumber' attach"
        n = remove_ansi_escape_sequence(get_output(cmd))
        if n == "0":
            return "Waiting for sync"
        else:
            return "Ready"


def get_raiden_status():
    # type: () -> str
    cmd = "docker-compose ps | grep raiden | sed -nE 's/.*:([0-9]+)-.*/\\1/p'"
    port = get_output(cmd)
    try:
        r = urlopen("http://localhost:%s/api/v1/tokens" % port)
        if r.getcode() == 200:
            return "Ready"
        else:
            return "Waiting for sync"
    except HTTPError:
        return "Waiting for sync"


def get_xud_status(cli):
    # type: (str) -> str
    cmd = cli + " getinfo -j | sed -n '1!p'"
    info = json.loads(get_output(cmd))
    lndMap = {x[0]: x[1] for x in info["lndMap"]}
    lndbtc_ok = lndMap["BTC"]["error"] == ""
    lndltc_ok = lndMap["LTC"]["error"] == ""
    raiden_ok = info["raiden"]["error"] == ""
    if lndbtc_ok and lndltc_ok and raiden_ok:
        return "Ready"
    else:
        return "Waiting for sync"


def get_status(service, stop_event):
    # type: (Service, threading.Event) -> str
    try:
        name = service.name
        cmd = "docker-compose ps -q {}".format(name)
        container_id = get_output(cmd)
        if len(container_id) == 0:
            return "Container not exist"

        cmd = "docker inspect -f '{{.State.Running}}' " + container_id
        running = get_output(cmd)
        if running == "false":
            return "Container down"

        if name == "bitcoind":
            cli = "docker-compose exec bitcoind bitcoin-cli -{} -rpcuser=xu -rpcpassword=xu".format(network)
            return get_bitcoind_kind_status(cli)
        elif name == "btcd":
            cli = "docker-compose exec btcd btcctl --{} --rpcuser=xu --rpcpass=xu".format(network)
            return get_bitcoind_kind_status(cli)
        elif name == "litecoind":
            cli = "docker-compose exec -T litecoind litecoin-cli -{} -rpcuser=xu -rpcpassword=xu".format(network)
            return get_bitcoind_kind_status(cli)
        elif name == "ltcd":
            cli = "docker-compose exec ltcd ltcctl --{} --rpcuser=xu --rpcpass=xu".format(network)
            return get_bitcoind_kind_status(cli)
        elif name == "lndbtc":
            cli = "docker-compose exec lndbtc lncli -n {} -c bitcoin".format(network)
            stop_event.wait(1)  # hacks to prevent concurrent getting status causing Ctrl-C not responding
            return get_lnd_kind_status(cli)
        elif name == "lndltc":
            cli = "docker-compose exec lndltc lncli -n {} -c litecoin".format(network)
            stop_event.wait(2)  # hacks to prevent concurrent getting status causing Ctrl-C not responding
            return get_lnd_kind_status(cli)
        elif name == "geth":
            stop_event.wait(5)  # hacks to prevent concurrent getting status causing Ctrl-C not responding
            cli = "docker-compose exec geth geth --{}".format(network)
            return get_geth_status(cli)
        elif name == "raiden":
            stop_event.wait(3)  # hacks to prevent concurrent getting status causing Ctrl-C not responding
            return get_raiden_status()
        elif name == "xud":
            stop_event.wait(4)  # hacks to prevent concurrent getting status causing Ctrl-C not responding
            cli = "docker-compose exec xud xucli"
            return get_xud_status(cli)
    except:
        logging.exception("Failed to fetch status for " + service.name)
    return ""


def draw_table(services):
    # type: ([Service]) -> (int, int)
    padding = 2
    headers = ["SERVICE", "STATUS"]
    w1 = max([len(s.display_name) for s in services] +
             [len(headers[0])]) + padding * 2

    w2 = max([len("") for s in services] +
             [len(headers[1]), 40]) + padding * 2

    #os.system("tput civis")  # hide cursor
    os.system("stty -echo")

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
            f("", w2, padding),
        ))
    print("┗{}┷{}┛".format(("━" * w1), ("━" * w2)))

    return padding, w2


def redraw_table(services, w2, padding, service, status):
    # type: ([Service], int, int, Service, str) -> None
    n = 0
    for i, s in enumerate(services):
        if s.name == service.name:
            n = (len(services) - i) * 2
            break

    s1 = "\033[{}A".format(n)
    s2 = "\033[{}B".format(n)
    content_format = "{{:{}s}}".format(w2 - padding * 2)
    content = content_format.format(status)
    update = "{}\033[15C{}\033[{}D{}".format(s1, content, 15 + len(content), s2)
    print(update, end="")
    sys.stdout.flush()


def gracefully_shutdown(stop_event, exit_code):
    stop_event.set()

    while True:
        n = len(threading.enumerate())
        logging.debug("running threads: %s", n)
        if n > 1:
            time.sleep(1)
        else:
            break

    logging.debug("only one thread now")

    #logging.debug("bash show cursor: tput cnorm")
    #os.system("tput cnorm")  # show cursor

    logging.debug("bash show input: stty sane")
    os.system("stty sane")
    #os.system("stty echo")

    # TODO clear stdin buffer
    exit(exit_code)


def pretty_print_statuses(services):
    q = Queue()
    stop_event = threading.Event()

    for service in services:
        service.start_status_query_thread(stop_event, q)

    padding, w2 = draw_table(services)

    try:
        ready_count = 0
        while ready_count < len(services):
            service, status = q.get()
            logging.debug("[STATUS] %s: %s", service.name, status)
            redraw_table(services, w2, padding, service, status)
            if status == "Ready":
                ready_count = ready_count + 1
    except KeyboardInterrupt:
        logging.debug("Ctrl-C detected")
        gracefully_shutdown(stop_event, 1)
    gracefully_shutdown(stop_event, 0)


def show_status():
    pretty_print_statuses(networks[network])


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
        # t2.start()  # When t1 t2 start at the same time it will break the bash prompt! WTF???
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
