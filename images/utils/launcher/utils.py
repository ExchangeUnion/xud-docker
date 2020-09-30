import logging
import os
from concurrent.futures import ThreadPoolExecutor, wait
import argparse

logger = logging.getLogger("launcher.utils")


class ParallelExecutionError(Exception):
    def __init__(self, failed):
        super()
        self.failed = failed


def parallel_execute(tasks, execute, timeout, print_failed, try_again, handle_result=None, single_thread=False):
    while len(tasks) > 0:
        failed = []
        if single_thread:
            workers = 1
        else:
            workers = len(tasks)
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="P") as executor:
            fs = {executor.submit(execute, t): t for t in tasks}
            done, not_done = wait(fs, timeout)
            for f in done:
                task = fs[f]
                try:
                    result = f.result()
                    if handle_result:
                        handle_result(task, result)
                except Exception as e:
                    failed.append((task, e))
            for f in not_done:
                task = fs[f]
                f.cancel()
                failed.append((task, TimeoutError("timeout")))
        if len(failed) > 0:
            print_failed(failed)
            if try_again():
                tasks = [f[0] for f in failed]
            else:
                raise ParallelExecutionError(failed)
        else:
            tasks = []


def get_useful_error_message(error):
    msg = str(error).strip()
    if len(msg) == 0:
        if isinstance(error, TimeoutError):
            return "timeout"
        else:
            return "%s" % type(error)
    return msg


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
