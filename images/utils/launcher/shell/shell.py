import sys
import os
import logging
from termios import *
import threading
from concurrent.futures import Future, CancelledError
from typing import Optional
import fcntl
import selectors
from queue import Queue

from .command import Command
from .history import History

from ..utils import get_hostfs_file

def output(seq):
    os.write(sys.stdout.fileno(), seq.encode())
    sys.stdout.flush()

# Indexes for termios list.
IFLAG = 0
OFLAG = 1
CFLAG = 2
LFLAG = 3
ISPEED = 4
OSPEED = 5
CC = 6


def _setraw(fd, when=TCSAFLUSH):
    """Put terminal into a raw mode."""
    mode = tcgetattr(fd)
    mode[IFLAG] = mode[IFLAG] & ~(BRKINT | ICRNL | INPCK | ISTRIP | IXON)
    # This OPOST flag is used to translate "\n" to "\r\n"
    #mode[OFLAG] = mode[OFLAG] & ~(OPOST)
    mode[CFLAG] = mode[CFLAG] & ~(CSIZE | PARENB)
    mode[CFLAG] = mode[CFLAG] | CS8
    mode[LFLAG] = mode[LFLAG] & ~(ECHO | ICANON | IEXTEN | ISIG)
    mode[CC][VMIN] = 1
    mode[CC][VTIME] = 0
    tcsetattr(fd, when, mode)


def _set_raw_nonblock(fd):
    # tty.setraw(self.fd)
    _setraw(fd)
    flag = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
    fcntl.fcntl(sys.stdin, fcntl.F_SETFL, flag | os.O_NONBLOCK)


def _reset_mode(fd, mode):
    tcsetattr(fd, TCSADRAIN, mode)


def _remove_oflag_opost(fd, when=TCSAFLUSH):
    mode = tcgetattr(fd)
    mode[OFLAG] = mode[OFLAG] & ~(OPOST)
    tcsetattr(fd, when, mode)


def _add_oflag_opost(fd, when=TCSAFLUSH):
    mode = tcgetattr(fd)
    mode[OFLAG] = mode[OFLAG] | OPOST
    tcsetattr(fd, when, mode)


class EventLoop(threading.Thread):
    _logger = logging.getLogger("launcher.shell.EventLoop")

    def __init__(self, queue, stop_event, fd):
        super().__init__(name="EventLoop")

        self.queue: Queue = queue
        self.stop_event: threading.Event = stop_event

        self.selector = selectors.DefaultSelector()
        self.selector.register(sys.stdin, selectors.EVENT_READ, self.callback)

        self._lock = threading.RLock()
        self.__socket = None

        self._ch_dict = {
            1: "ctrl_a",
            2: "ctrl_b",
            3: "ctrl_c",
            4: "ctrl_d",
            5: "ctrl_e",
            6: "ctrl_f",
            9: "tab",
            12: "ctrl_l",
            13: "enter",
            21: "ctrl_u",
            27: "esc"
        }
        self._fd = fd

    @property
    def socket(self):
        with self._lock:
            return self.__socket

    @socket.setter
    def socket(self, value):
        with self._lock:
            self.__socket = value
            if value is None:
                _add_oflag_opost(sys.stdin.fileno())
            else:
                _remove_oflag_opost(sys.stdin.fileno())

    def decode_input(self, data):
        i = 0
        esc_i = -1
        while i < len(data):
            b = ord(data[i])

            if esc_i == 0:
                if data[i] == '[':
                    esc_i = 1
                    i = i + 1
                    continue
                else:
                    esc_i = -1
                    self.queue.put("esc")

            if esc_i == 1:
                if data[i] == 'A':
                    esc_i = -1
                    self.queue.put("arrow_up")
                    i = i + 1
                    continue
                elif data[i] == 'B':
                    esc_i = -1
                    self.queue.put("arrow_down")
                    i = i + 1
                    continue
                elif data[i] == 'C':
                    esc_i = -1
                    self.queue.put("arrow_right")
                    i = i + 1
                    continue
                elif data[i] == 'D':
                    esc_i = -1
                    self.queue.put("arrow_left")
                    i = i + 1
                    continue
                else:
                    esc_i = -1
                    self.queue.put("esc")
                    self.queue.put("[")

            ch = None

            if b < 0:
                raise Exception(f"Illegal byte: {b!r}")
            elif b < 32:
                # control characters:
                if b == 27:
                    if i + 1 < len(data) and data[i + 1] == '[':
                        # decode ANSI escape sequences
                        esc_i = 0
                        i = i + 1
                        continue
                ch = self._ch_dict.get(b, None)
            elif b < 127:
                # printable characters:
                ch = data[i]
            elif b == 127:
                # del
                ch = 'del'
            else:
                # >= 128 characters UTF-8 Unicode characters
                pass

            if ch:
                self.queue.put(ch)

            i = i + 1

    def callback(self, stdin, mask):
        with self._lock:
            data = stdin.read()
            if self.socket:
                try:
                    self.socket.send(data.encode())
                    return
                except:
                    self._logger.exception("Failed to send data to socket")
                    self.socket = None

            self.decode_input(data)

    def _loop(self):
        try:
            while not self.stop_event.is_set():
                events = self.selector.select(timeout=1)
                for key, mask in events:
                    callback = key.data
                    callback(key.fileobj, mask)
        except:
            self._logger.exception("The loop exits unexpectedly")

    def run(self) -> None:
        self._logger.debug("Begin")

        mode = tcgetattr(self._fd)
        _set_raw_nonblock(self._fd)

        try:
            while not self.stop_event.is_set():
                events = self.selector.select(timeout=1)
                for key, mask in events:
                    callback = key.data
                    callback(key.fileobj, mask)
        except:
            self._logger.exception("The loop exits unexpectedly")
        finally:
            _reset_mode(self._fd, mode)

        self._logger.debug("End")

    def interrupt(self):
        try:
            self.queue.put("eof")  # enqueue EOF (Ctrl + D)
            self.selector.close()
        except:
            self._logger.exception("Failed to interrupt")


class InputHandler(threading.Thread):
    _logger = logging.getLogger("launcher.shell.InputHandler")

    def __init__(self, queue, stop_event):
        super().__init__(name="InputHandler")

        self.queue: Queue = queue
        self.stop_event: threading.Event = stop_event

        self._lock = threading.RLock()

        self._cmd: Command = Command()
        self._history: Optional[History] = None

        self.__prompt = ""
        self.__command_handler = None
        self.__accept_input = False
        self.__enable_history = True
        self.__answer: Optional[Future] = None

    @property
    def prompt(self):
        with self._lock:
            return self.__prompt

    @prompt.setter
    def prompt(self, value):
        with self._lock:
            self.__prompt = value

    @property
    def command_handler(self):
        with self._lock:
            return self.__command_handler

    @command_handler.setter
    def command_handler(self, value):
        with self._lock:
            self.__command_handler = value

    @property
    def accept_input(self):
        with self._lock:
            return self.__accept_input

    @accept_input.setter
    def accept_input(self, value):
        with self._lock:
            self.__accept_input = value

    @property
    def enable_history(self):
        with self._lock:
            return self.__enable_history

    @enable_history.setter
    def enable_history(self, value):
        with self._lock:
            self.__enable_history = value

    @property
    def answer(self):
        with self._lock:
            return self.__answer

    @answer.setter
    def answer(self, value):
        with self._lock:
            self.__answer = value

    def set_network_dir(self, network_dir):
        with self._lock:
            self._history = History(self._cmd, f"{network_dir}/history")

    def _history_reset(self):
        if self._history is None or not self.enable_history:
            return
        self._history.reset()

    def _history_commit(self, cmd):
        if self._history is None or not self.enable_history:
            return
        self._history.commit(cmd)

    def _history_prev(self):
        if self._history is None or not self.enable_history:
            return
        self._history.prev()

    def _history_next(self):
        if self._history is None or not self.enable_history:
            return
        self._history.next()

    def _handle_command(self, cmd: str):
        try:
            if self.command_handler is not None:
                #self.accept_input = False
                # TODO disable input
                self.command_handler(cmd)  # sync
                # TODO enable input
                #self.accept_input = True
        except:
            self._logger.exception("Failed to execute command: %r", cmd)

    def _handle_input(self, ch):
        with self._lock:
            cmd = self._cmd

            if ch == "eof":
                return False

            if not self.accept_input:
                if ch == "ctrl_c":
                    return False
                return True

            if ch == "arrow_up":
                self._history_prev()
            elif ch == "arrow_down":
                self._history_next()
            elif ch == "arrow_right":
                cmd.move_forward()
            elif ch == "arrow_left":
                cmd.move_backward()
            elif ch == "ctrl_a":
                cmd.move_begin()
            elif ch == "ctrl_b":  # Ctrl + B
                cmd.move_backward()
            elif ch == "ctrl_c":  # Ctrl + C
                cmd.reset()
                output("^C")
                if self.answer is not None:
                    return False
                else:
                    output("\n")
                    output(self.prompt)
                    self._history_reset()
            elif ch == "ctrl_e":
                cmd.move_end()
            elif ch == "ctrl_f":
                cmd.move_forward()
            elif ch == "tab":
                # TODO tab completion
                pass
            elif ch == "ctrl_l":
                output(f'\033[2J\033[1;1H')
                output(self.prompt)
                cmd.print()
            elif ch == "enter":
                output("\n")
                if self.answer is not None:
                    cmd_str = str(cmd)
                    self.answer.set_result(cmd_str)
                    self.accept_input = False
                    cmd.reset()
                    return True
                else:
                    if not cmd.is_empty():
                        if cmd.is_exit():
                            return False
                        elif str(cmd) == "down":
                            self._handle_command(str(cmd))
                            return False
                        else:
                            self._handle_command(str(cmd))
                            self._history_commit(cmd)  # will reset history too
                    else:
                        self._history_reset()
                    output(self.prompt)
                    cmd.reset()
            elif ch == "ctrl_u":
                cmd.delete_to_begin()
            elif ch == "del":  # DEL
                cmd.delete_backward()
            elif len(ch) == 1:
                cmd.append_character(ch)
                self._history_reset()
            else:
                self._logger.warning(f"Discard {ch=}")

            return True

    def run(self) -> None:
        self._logger.debug("Begin")

        try:
            while True:
                ch = self.queue.get()
                if not self._handle_input(ch):
                    break
        except:
            self._logger.exception("The loop exits unexpectedly")

        self._logger.debug("End")
        self.stop_event.set()
        if self.answer is not None and not self.answer.cancelled():
            self.answer.cancel()


class Shell:
    def __init__(self):
        self._logger = logging.getLogger("launcher.shell.Shell")

        with open(os.path.dirname(__file__) + '/banner.txt') as f:
            self._banner = "".join(f.readlines())

        self.fd_in = sys.stdin.fileno()
        self.fd_out = sys.stdout.fileno()
        self.fd_err = sys.stderr.fileno()

        queue = Queue()
        stop_event = threading.Event()

        self.stop_event = stop_event
        self.loop = EventLoop(queue, stop_event, self.fd_in)
        self.handler = InputHandler(queue, stop_event)

        self.loop.start()
        self.handler.start()

    def print_banner(self):
        self.print(self._banner)

    def start(self, prompt, command_handler):
        self.print_banner()

        self.handler.prompt = prompt
        self.handler.command_handler = command_handler
        output(prompt)
        self.handler.accept_input = True
        self.handler.enable_history = True

        self.stop_event.wait()

    def input(self, prompt: str) -> str:
        assert self.handler.answer is None

        old_prompt = self.handler.prompt
        old_accept_input = self.handler.accept_input
        old_enable_history = self.handler.enable_history

        self.handler.prompt = prompt
        self.handler.accept_input = True
        self.handler.enable_history = False
        self.handler.answer = Future()

        output(prompt)

        try:
            result = self.handler.answer.result()
        except CancelledError:
            raise KeyboardInterrupt()
        finally:
            self.handler.prompt = old_prompt
            self.handler.accept_input = old_accept_input
            self.handler.enable_history = old_enable_history
            self.handler.answer = None

        return result

    def yes_or_no(self, prompt: str) -> str:
        while True:
            answer = self.input(prompt + " [Y/n] ").lower()
            if answer == "y" or answer == "yes" or len(answer) == 0:
                return "yes"
            elif answer == "n" or answer == "no":
                return "no"

    def no_or_yes(self, prompt: str) -> str:
        while True:
            answer = self.input(prompt + " [y/N] ").lower()
            if answer == "n" or answer == "no" or len(answer) == 0:
                return "no"
            if answer == "y" or answer == "yes":
                return "yes"

    def confirm(self, prompt: str) -> bool:
        answer = self.input(prompt)
        return len(answer) == 0

    def redirect_stdin(self, socket):
        self.loop.socket = socket

    def stop_redirect_stdin(self):
        self.loop.socket = None

    def stop(self):
        self._logger.debug("stop")
        self.loop.interrupt()

    def set_network_dir(self, network_dir):
        self.handler.set_network_dir(network_dir)

    def print(self, text):
        print(text, end="")
        sys.stdout.flush()

    def println(self, line):
        print(line)
