from abc import ABCMeta

from .abc import Service


class Lnd(Service, metaclass=ABCMeta):
    pass
