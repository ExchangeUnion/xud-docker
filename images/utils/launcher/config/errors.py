import argparse


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


class InvalidHomeDir(Exception):
    def __init__(self, reason):
        super().__init__(reason)


class InvalidNetworkDir(Exception):
    def __init__(self, reason):
        super().__init__(reason)


class NetworkConfigFileValueError(ValueError):
    def __init__(self, hint):
        super().__init__(hint)


class CommandLineArgumentValueError(ValueError):
    def __init__(self, hint):
        super().__init__(hint)


class NetworkConfigFileSyntaxError(SyntaxError):
    def __init__(self, hint):
        super().__init__(hint)
