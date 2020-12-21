import sys
import logging


def output(seq):
    print(seq, end="")
    sys.stdout.flush()


class Command:
    _logger = logging.getLogger("launcher.shell.Command")

    def __init__(self):
        self.value = ""
        self.uncommitted_value = None
        self.index = 0

    def append_character(self, c):
        if self.index < len(self.value):
            head = self.value[:self.index]
            tail = self.value[self.index:]
            self.value = head + c + tail
            self.index += 1
            output("%s%s\033[%dD" % (c, tail, len(tail)))
        else:
            self.value += c
            self.index += 1
            output(c)

    def print(self):
        if self.index < len(self.value):
            output("%s\033[%dD" % (self.value, len(self.value) - self.index))
        else:
            output(self.value)

    def reset(self):
        self.value = ""
        self.index = 0
        self.uncommitted_value = None

    def clear(self):
        raise NotImplementedError()

    def __repr__(self):
        return f"<Command value={self.value} index={self.index} uncommitted={self.uncommitted_value}>"

    def __str__(self):
        return self.normalized_value

    @property
    def normalized_value(self):
        return self.value.strip()

    def is_exit(self):
        cmd = self.normalized_value.lower()
        return cmd == "exit" or cmd == "quit"

    def is_empty(self):
        return len(self.normalized_value) == 0

    def change(self, new_cmd):
        if self.uncommitted_value is None:
            self.uncommitted_value = self.value
        self.move_begin()
        self.value = new_cmd
        self.index = len(self.value)
        output("\033[K%s" % self.value)

    def restore(self):
        if self.uncommitted_value is not None:
            self.move_begin()
            self.value = self.uncommitted_value
            self.index = len(self.value)
            output("\033[K%s" % self.value)
            self.uncommitted_value = None

    def delete_backward(self):
        if self.index > 0:
            head = self.value[:self.index - 1]
            tail = self.value[self.index:]
            self.value = head + tail
            if len(tail) > 0:
                output('\b\033[K%s\033[%dD' % (tail, len(tail)))
            else:
                output('\b\033[K')
            self.index = len(head)

    def delete_forward(self):
        raise NotImplementedError()

    def delete_to_begin(self):
        if self.index < len(self.value):
            tail = self.value[self.index:]
            output("\033[%dD\033[K%s\033[%dD" % (self.index, tail, len(tail)))
            self.value = tail
            self.index = 0
        else:
            output("\033[%dD\033[K" % self.index)
            self.value = ""
            self.index = 0

    def move_backward(self):
        if self.index > 0:
            self.index -= 1
            output("\033[1D")

    def move_backward_word(self):
        raise NotImplementedError()

    def move_forward(self):
        if self.index < len(self.value):
            self.index += 1
            output("\033[1C")

    def move_forward_word(self):
        raise NotImplementedError()

    def move_begin(self):
        if self.index > 0:
            output("\033[%dD" % self.index)
            self.index = 0

    def move_end(self):
        if self.index < len(self.value):
            output(f"\033[%dC" % (len(self.value) - self.index))
            self.index = len(self.value)
