import re
import argparse


class PortPublish:
    def __init__(self, value: str):
        p1 = re.compile(r"^(\d+)$")  # 8080
        p2 = re.compile(r"^(\d+):(\d+)$")  # 80:8080
        p3 = re.compile(r"^(\d+):(\d+):(\d+)$")  # 127.0.0.1:80:8080

        protocol = "tcp"
        if "/" in value:
            parts = value.split("/")
            p = parts[0]
            protocol = parts[1]
            if protocol not in ["tcp", "udp", "sctp"]:
                raise ValueError("Invalid protocol: {} ({})".format(protocol, p))

        host = None
        host_port = None
        port = None

        m = p1.match(value)
        if m:
            port = int(m.group(1))
            host_port = port
        else:
            m = p2.match(value)
            if m:
                host_port = int(m.group(1))
                port = int(m.group(2))
            else:
                m = p3.match(value)
                if m:
                    host = m.group(1)
                    host_port = int(m.group(2))
                    port = int(m.group(3))

        self.protocol = protocol
        self.host = host
        self.host_port = host_port
        self.port = port

    def __eq__(self, other):
        if not isinstance(other, PortPublish):
            return False
        if self.host != other.host:
            return False
        if self.host_port != other.host_port:
            return False
        if self.port != other.port:
            return False
        if self.protocol != other.protocol:
            return False
        return True

    def __str__(self):
        return "{}:{}:{}/{}".format(self.host, self.host_port, self.port, self.protocol)

    def __hash__(self):
        return self.__str__().__hash__()


class VolumeMapping:
    def __init__(self, value: str):
        self.host_dir, self.container_dir = value.split(":")
        self.mode = "rw"

    def __eq__(self, other):
        if not isinstance(other, VolumeMapping):
            return False
        if self.host_dir != other.host_dir:
            return False
        if self.container_dir != other.container_dir:
            return False
        if self.mode != other.mode:
            return False
        return True

    def __str__(self):
        return "{}:{}:{}".format(self.host_dir, self.container_dir, self.mode)

    def __hash__(self):
        return self.__str__().__hash__()


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
