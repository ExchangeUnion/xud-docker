from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar, Iterable, Iterator, get_args, Optional
from dataclasses import dataclass

from ..options import Option, ExposePortsOption, DisabledOption

if TYPE_CHECKING:
    from ..presets import Preset
    from ..docker import DockerFactory


class ServiceOptions(Iterable[Option]):
    def __init__(self, service: Service):
        self.expose_ports = ExposePortsOption(service)
        self.disabled = DisabledOption(service)

    def __iter__(self) -> Iterator[Option]:
        opts = [a for a in dir(self) if not a.startswith("__") and not callable(getattr(self, a))]
        yield from opts


@dataclass
class ServiceStatus:
    container: str
    application: Optional[str]


T = TypeVar('T', bound=ServiceOptions)


class Service(Generic[T], metaclass=ABCMeta):
    options: T

    def __init__(self, preset: Preset, name: str, image: str):
        self.preset = preset
        self.name = name
        self.image = self._docker_factory.create_image(image)
        self.container = self._docker_factory.create_container(f"{preset.prefix}_{name}_1")
        self.options = get_args(self.__class__.__orig_bases__[0])[0](self)

    @property
    def _docker_factory(self) -> DockerFactory:
        return self.preset.config.docker_factory

    @property
    def prefix(self) -> str:
        return self.preset.prefix

    def configure(self, parser):
        for opt in self.options:
            opt.configure(parser)

    def start(self) -> None:
        self.container.start()

    def stop(self) -> None:
        self.container.stop()

    def create(self) -> None:
        self.image.create()
        self.container.create()

    def destroy(self) -> None:
        self.container.destroy()
        self.image.destroy()

    @abstractmethod
    @property
    def command(self) -> [str]:
        pass

    @abstractmethod
    @property
    def environment(self) -> [str]:
        pass

    @abstractmethod
    @property
    def application_status(self) -> str:
        pass

    @property
    def status(self) -> ServiceStatus:
        container_status = self.container.status
        if container_status == "running":
            try:
                application_status = self.application_status
                return ServiceStatus(
                    container=container_status,
                    application=application_status,
                )
            except Exception as e:
                return ServiceStatus(
                    container=container_status,
                    application=str(e),
                )
        else:
            return ServiceStatus(
                container=container_status,
                application=None,
            )


class NodeApi:
    def __init__(self, node: Node):
        self.node = node


A = TypeVar('A', bound=NodeApi)


class Node(Generic[T, A], Service[T], metaclass=ABCMeta):

    def __init__(self, preset: Preset, name: str, image: str):
        super().__init__(preset, name, image)
        self.api: A = get_args(self.__class__.__orig_bases__[1])[0](self)

    @abstractmethod
    @property
    def cli_command(self) -> Optional[str]:
        pass

    def cli(self, args: str) -> bytes:
        return b''
