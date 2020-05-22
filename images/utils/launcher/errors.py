class ImagesCheckAbortion(Exception):
    def __init__(self, failed):
        super().__init__()
        self.failed = failed


class ContainersCheckAbortion(Exception):
    def __init__(self, failed):
        super().__init__()
        self.failed = failed


class ContainersEnsureAbortion(Exception):
    def __init__(self, failed):
        super().__init__()
        self.failed = failed


class ContainerNotFound(Exception):
    def __init__(self, container):
        super().__init__(container)
        self.container = container


class NetworkConfigFileSyntaxError(SyntaxError):
    def __init__(self, hint):
        super().__init__(hint)


class NetworkConfigFileValueError(ValueError):
    def __init__(self, hint):
        super().__init__(hint)


class CommandLineArgumentValueError(ValueError):
    def __init__(self, hint):
        super().__init__(hint)


class InvalidImageName(Exception):
    def __init__(self, name):
        super().__init__(name)


class FatalError(Exception):
    pass
