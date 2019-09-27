from subprocess import Popen, PIPE
import time
import sys
import fcntl
import os
import re


def set_non_blocking(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    flags = flags | os.O_NONBLOCK
    fcntl.fcntl(fd, fcntl.F_SETFL, flags)


def invoke_create():
    p = Popen(["docker-compose", "exec", "xud", "xucli", "create"], stdout=PIPE, stderr=PIPE, bufsize=0)
    set_non_blocking(p.stdout)
    set_non_blocking(p.stderr)

    while True:
        out = p.stdout.read()
        if out is None:
            time.sleep(1)
            continue
        out = out.decode()
        out = re.sub(r'D0925.*used\r\n', '', out)
        idx = out.find("You")
        out = out[idx:]
        print(out, end="")
        sys.stdout.flush()
        if "Enter a password" in out:
            break
        time.sleep(1)
        print(".")

    while True:
        out = p.stdout.read()
        if out is None:
            time.sleep(1)
            continue
        out = out.decode()
        print(out, end="")
        sys.stdout.flush()
        if "Re-enter password" in out:
            break
        time.sleep(1)

    while True:
        out = p.stdout.read()
        if out is None:
            time.sleep(1)
            continue
        out = out.decode()
        if len(out.strip()) == 0:
            time.sleep(1)
            continue
        print(out, end="")
        sys.stdout.flush()
        if "SEED" in out:
            return
        elif "Passwords do not match, please try again" in out:
            raise Exception("PASSWORD_NOT_MATCH")
        elif "password must be at least 8 characters" in out:
            raise Exception("INVALID_PASSWORD")
        elif "xud was initialized without a seed because no wallets could be initialized" in out:
            raise Exception("UNEXPECTED_ERROR")
        elif "ERROR" in out:
            raise Exception("UNEXPECTED_ERROR")
        time.sleep(1)


ok = False
counter = 0

while not ok and counter < 3:
    counter = counter + 1
    try:
        invoke_create()
        ok = True
    except KeyboardInterrupt:
        print()
        exit(1)
    except Exception as e:
        if str(e) == "UNEXPECTED_ERROR":
            exit(1)
    print()

if not ok:
    exit(1)
else:
    input("YOU WILL NOT BE ABLE TO DISPLAY YOUR XUD SEED AGAIN. Press ENTER to continue...")
