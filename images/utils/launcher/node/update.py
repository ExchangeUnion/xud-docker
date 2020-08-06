from __future__ import annotations
from typing import Optional, Dict, List, TYPE_CHECKING, Set
from enum import Enum
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, wait
import time
from yaml import load
import logging

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from .docker_registry_client import DockerTemplate, ImageMetadata

if TYPE_CHECKING:
    from . import NodeManager


class ServiceStatus(Enum):
    UP_TO_DATE = 0
    OUTDATED = 1
    MISSING = 2
    DISABLED = 3


@dataclass
class Image:
    name: str
    digest: str = None


@dataclass
class ImageDiff:
    old: str = None
    new: str = None


@dataclass
class CommandDiff:
    old: str = None
    new: str = None


@dataclass
class EnvironmentDiff:
    old: List[str] = None
    new: List[str] = None


@dataclass
class PortsDiff:
    old: List[str] = None
    new: List[str] = None


@dataclass
class VolumesDiff:
    old: List[str] = None
    new: List[str] = None


@dataclass
class ServiceDetails:
    status: ServiceStatus
    image: ImageDiff = None
    command: CommandDiff = None
    environment: EnvironmentDiff = None
    ports: PortsDiff = None
    volumes: VolumesDiff = None


@dataclass
class ImageDetails:
    name: str
    branch: str
    local: Optional[ImageMetadata]
    registry: Optional[ImageMetadata]

    @property
    def branch_image(self) -> str:
        if self.branch == "master":
            return self.name
        else:
            branch = self.branch.replace("/", "-")
            return "%s__%s" % (self.name, branch)

    @property
    def pull(self) -> Image:
        if not self.local:
            if not self.registry:
                raise RuntimeError("Image %s not found" % self.name)
            return Image(name="{}:{}".format(self.registry.repo, self.registry.tag), digest=self.registry.digest)


@dataclass
class UpdateDetails:
    services: Dict[str, ServiceDetails]
    images: Dict[str, ImageDetails]


@dataclass
class ServiceDef:
    name: str
    image: str
    command: str
    environment: List[str]
    ports: List[str]
    volumes: List[str]


def _normalize_image(name) -> str:
    if ":" in name:
        repo, tag = name.split(":")
    else:
        repo = name
        tag = "latest"
    return "{}:{}".format(repo, tag)


def _parse_service_yaml(name, service) -> ServiceDef:
    image = service["image"]
    image = _normalize_image(image)

    command = service["command"] or ""

    environment = service["environment"] or []
    environment = sorted(environment)

    ports = service["ports"] or []
    ports = sorted(ports)

    volumes = service["volumes"] or []
    volumes = sorted(volumes)

    return ServiceDef(name=name, image=image, command=command, environment=environment, ports=ports, volumes=volumes)


def _get_branch_tag(tag, branch) -> str:
    branch = branch.replace("/", "-")
    return "{}__{}".format(tag, branch)


class UpdateManager:
    def __init__(self, node_manager: NodeManager):
        self.logger = logging.getLogger("launcher.node.UpdateManager")
        self.node_manager = node_manager
        self.docker_template = DockerTemplate()

    def _fetch_metadata(self, images: List[str], branch: str, get_fn) -> Dict[str, ImageMetadata]:
        tasks = images

        def get_metadata(image: str) -> Optional[ImageMetadata]:
            repo, tag = image.split(":")
            m = None
            if branch != "master":
                m = get_fn(repo, _get_branch_tag(tag, branch))
            if not m:
                m = get_fn(repo, tag)
            return m

        result = {}

        retry_delay = 3

        while len(tasks) > 0:
            failed = []
            with ThreadPoolExecutor(max_workers=len(tasks), thread_name_prefix="Update") as executor:
                fs = {executor.submit(get_metadata, t): t for t in tasks}
                done, not_done = wait(fs, 30)
                for f in done:
                    task = fs[f]
                    try:
                        metadata = f.result()
                        result[task] = metadata
                    except Exception as e:
                        failed.append((task, e))
                for f in not_done:
                    task = fs[f]
                    failed.append((task, TimeoutError()))
                print(result)
                tasks = []
                for image, exception in failed:
                    tasks.append(image)
                    logging.debug("Failed to fetch metadata for image %s", image, exception)
                time.sleep(retry_delay)
        return result

    def _check_images(self, images: List[str], details: UpdateDetails):
        branch = self.node_manager.config.branch

        local_metadata = self._fetch_metadata(images, branch, self.docker_template.get_registry_image_metadata)
        registry_metadata = self._fetch_metadata(images, branch, self.docker_template.get_local_image_metadata)

        # Update details
        for image in images:
            details.images[image] = ImageDetails(
                name=image,
                branch=branch,
                local=local_metadata.get(image, None),
                registry=registry_metadata.get(image, None),
            )

    def check_for_updates(self) -> Optional[UpdateDetails]:
        current_compose = self.node_manager.current_compose_file
        with open(current_compose) as f:
            current_compose = load(f, Loader=Loader)

        result = UpdateDetails(services={}, images={})
        images = set()
        for name, service in current_compose["services"].items():
            service = _parse_service_yaml(name, service)
            result.services[name] = ServiceDetails(
                status=ServiceStatus.UP_TO_DATE,
                image=ImageDiff(new=service.image),
                command=CommandDiff(new=service.command),
                environment=EnvironmentDiff(new=service.environment),
                ports=PortsDiff(new=service.ports),
                volumes=VolumesDiff(new=service.volumes),
            )
            images.add(service.image)

        images = list(images)

        self._check_images(images, result)

        previous_compose = self.node_manager.previous_compose_file
        if previous_compose:
            with open(previous_compose) as f:
                previous_compose = load(f, Loader=Loader)
            for name, service in previous_compose["services"].items():
                service = _parse_service_yaml(name, service)
                if name in result.services:
                    result.services[name] = ServiceDetails(
                        status=ServiceStatus.DISABLED,
                        image=ImageDiff(old=service.image),
                        command=CommandDiff(old=service.command),
                        environment=EnvironmentDiff(old=service.environment),
                        ports=PortsDiff(old=service.ports),
                        volumes=VolumesDiff(old=service.volumes),
                    )
                else:
                    svc = result.services[name]
                    svc.image.old = Image(service.image)
                    svc.command.old = service.command
                    svc.environment.old = sorted(service.environment)
                    svc.ports.old = sorted(service.ports)
                    svc.volumes.old = sorted(service.volumes)
                    # TODO diff

        # TODO diff current running containers

        up_to_date = True
        for service in result.services.values():
            if service.status != ServiceStatus.UP_TO_DATE:
                up_to_date = False
                break
        if up_to_date:
            result = None

        return result

    def apply(self, updates: UpdateDetails) -> None:
        # TODO update images

        # TODO update containers
        for service in updates.services.values():
            if service.status == ServiceStatus.MISSING:
                pass  # TODO create container
            elif service.status == ServiceStatus.DISABLED:
                pass  # TODO stop & remove container
            elif service.status == ServiceStatus.OUTDATED:
                pass  # TODO stop & recreate container
