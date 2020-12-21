class InvalidNetwork(Exception):
    pass


class InvalidService(Exception):
    pass


class ForbiddenService(Exception):
    pass


class UnsupportedFieldType(Exception):
    pass


class ServiceNotFound(Exception):
    pass


class SubprocessError(Exception):
    def __init__(self, exit_code: int, message: str):
        super().__init__(message)
        self.exit_code = exit_code


class FatalError(Exception):
    pass


class NoProcess(Exception):
    pass


class NoInfuraSimnet(Exception):
    pass
