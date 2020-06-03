from __future__ import annotations
from typing import TYPE_CHECKING, Generic, TypeVar, Iterable, Iterator, get_args
from abc import ABCMeta, abstractmethod
from ..options import Option, DirOption, ExposePortsOption, DisabledOption
if TYPE_CHECKING:
    from ..presets import Preset


class ServiceOptions(Iterable[Option]):
    def __init__(self, service: Service):
        self.expose_ports = ExposePortsOption(service)
        self.disabled = DisabledOption(service)

    def __iter__(self) -> Iterator[Option]:
        opts = [a for a in dir(self) if not a.startswith("__") and not callable(getattr(self, a))]
        yield from opts


T = TypeVar('T', bound=ServiceOptions)


class Service(Generic[T], metaclass=ABCMeta):
    _options: T

    def __init__(self, preset: Preset, name: str, image: str):
        self.preset = preset
        self.name = name
        self.image = image
        self._options = get_args(self.__class__.__orig_bases__[0])[0](self)

    def configure(self, parser):
        for opt in self._options:
            opt.configure(parser)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def create(self) -> None:
        pass

    def remove(self) -> None:
        pass
