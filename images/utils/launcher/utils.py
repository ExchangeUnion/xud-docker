import argparse
import logging
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Callable, TypeVar
from launcher.errors import ParallelError

logger = logging.getLogger(__name__)


def normalize_path(path: str) -> str:
    parts = path.split("/")
    pwd: str = os.environ["HOST_PWD"]
    home: str = os.environ["HOST_HOME"]

    # expand ~
    while "~" in parts:
        i = parts.index("~")
        if i + 1 < len(parts):
            parts = parts[:i] + home.split("/") + parts[i + 1:]
        else:
            parts = parts[:i] + home.split("/")

    if len(parts[0]) > 0:
        parts = pwd.split("/") + parts

    # remove all '.'
    if "." in parts:
        parts.remove(".")

    # remove all '..'
    if ".." in parts:
        parts = [p for i, p in enumerate(parts) if i + 1 < len(parts) and parts[i + 1] != ".." or i + 1 == len(parts)]
        parts.remove("..")

    return "/".join(parts)


def get_hostfs_file(file):
    return "/mnt/hostfs" + file


class ArgumentError(Exception):
    def __init__(self, message, usage):
        super().__init__(message)
        self.usage = usage


class ArgumentParser(argparse.ArgumentParser):
    """
    https://stackoverflow.com/questions/5943249/python-argparse-and-controlling-overriding-the-exit-status-code
    """

    def error(self, message):
        raise ArgumentError(message, self.format_usage())


def yes_or_no(prompt, default="yes"):
    assert default in ["yes", "no"]
    while True:
        if default == "yes":
            reply = input(prompt + " [Y/n] ")
        else:
            reply = input(prompt + " [y/N] ")
        reply = reply.strip().lower()
        if reply == "":
            return default
        if reply in ["y", "yes"]:
            return "yes"
        if reply in ["n", "no"]:
            return "no"


def get_percentage(current, total):
    if total == 0:
        return "0.00%% (%d/%d)" % (current, total)
    if current >= total:
        return "100.00%% (%d/%d)" % (current, total)
    p = current / total * 100
    if p > 0.005:
        p = p - 0.005
    else:
        p = 0
    return "%.2f%% (%d/%d)" % (p, current, total)


def color(text: str) -> str:
    if text == "done":
        return "\033[32mdone\033[0m"
    elif text == "error":
        return "\033[31merror\033[0m"
    else:
        return text


T = TypeVar('T')


def parallel(
        executor: ThreadPoolExecutor,
        items: List[T],
        linehead: Callable[[T], str],
        run: Callable[[T, threading.Event], None]
):
    result = {item: None for item in items}
    stop = threading.Event()

    def animate():
        nonlocal result
        nonlocal stop

        lines = []
        width = 0
        for item in items:
            line = linehead(item)
            line = line.capitalize()
            if len(line) > width:
                width = len(line)
            lines.append(line)
        fmt = "%-{}s ...".format(width)
        lines = [fmt % line for line in lines]
        print("\n".join(lines))

        i = 0
        error = False
        while not stop.is_set():
            print("\033[%dA" % len(items), end="", flush=True)
            finish = 0
            for item in items:
                r = result[item]
                if r:
                    if r == "error":
                        error = True
                    suffix = "... " + color(r)
                    suffix_len = 4 + len(r)
                    finish += 1
                else:
                    suffix = "%-3s" % ("." * abs(3 - i % 6))
                    suffix_len = 3
                print("\033[%dC" % (width + 1), end="", flush=True)
                print(suffix, end="", flush=True)
                print("\033[%dD\033[1B" % (width + 1 + suffix_len), end="", flush=True)
            print("\033[K", end="", flush=True)
            if finish == len(items):
                break
            stop.wait(0.5)
            i += 1

        if error:
            # TODO create ParallelError with all task errors
            raise ParallelError

    def wrapper(item):
        nonlocal result
        nonlocal stop
        try:
            run(item, stop)
            # time.sleep(random.randint(3, 10))
            result[item] = "done"
        except Exception as e:
            logger.exception("[Parallel] %s: %s", linehead(item), str(e))
            result[item] = "error"

    f = executor.submit(animate)
    try:
        for item in items:
            executor.submit(wrapper, item)
        f.result()
    finally:
        stop.set()
