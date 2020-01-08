import sys
import logging
from .command import Command


def output(seq):
    print(seq, end="")
    sys.stdout.flush()


class History:
    _logger = logging.getLogger("launcher.shell.History")

    def __init__(self, cmd: Command, history_file):
        self.cmd = cmd
        self._history_file = history_file

        self.history = []
        self.index = 0
        try:
            with open(self._history_file) as f:
                for line in f.readlines():
                    if line.endswith("\n"):
                        line = line[:-1]
                    if len(line) > 0:
                        self.history.append(line)
                self.index = len(self.history)
        except FileNotFoundError:
            with open(self._history_file, 'w'):
                pass

    def prev(self):
        if self.index > 0:
            self.index -= 1
            new_cmd = self.history[self.index]
            self.cmd.change(new_cmd)
        else:
            self._logger.debug("No prev history")

    def next(self):
        if self.index < len(self.history) - 1:
            self.index += 1
            new_cmd = self.history[self.index]
            self.cmd.change(new_cmd)
        elif self.index == len(self.history) - 1:
            self.cmd.restore()
            self.index += 1
        else:
            self._logger.debug("No next history")

    def commit(self, cmd: Command):
        self._logger.debug("Committing command: %r", cmd)
        cmd_str = str(cmd)
        self.history.append(cmd_str)
        try:
            with open(self._history_file, 'a') as f:
                f.write(cmd_str + "\n")
        except FileNotFoundError:
            with open(self._history_file, 'w') as f:
                f.write(cmd_str + "\n")
        cmd.reset()
        self.reset()

    def reset(self):
        self.index = len(self.history)

    def __repr__(self):
        return f"<History history={self.history} index={self.index}>"
