class ExecutionError(Exception):
    def __init__(self, message: str, exit_code: int, output: str):
        super().__init__(message)
        self.exit_code = exit_code
        self.output = output


class ParseError(Exception):
    pass


class InvalidNetwork(Exception):
    pass


class InvalidService(Exception):
    pass


class ForbiddenService(Exception):
    pass


class UnsupportedFieldType(Exception):
    pass


class FatalError(Exception):
    pass


class NoProcess(Exception):
    pass


class NoInfuraSimnet(Exception):
    pass


class ContainerNotFound(Exception):
    pass


class ServiceNotFound(Exception):
    pass


class SetupError(Exception):
    pass
