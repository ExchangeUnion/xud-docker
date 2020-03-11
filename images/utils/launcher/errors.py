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
