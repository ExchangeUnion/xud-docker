from __future__ import annotations
from typing import Optional, Dict, List, TYPE_CHECKING, Set
from enum import Enum
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, wait
import time
from yaml import load
import logging
import traceback

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
class ServiceDef:
    name: str
    image: str
    command: str
    environment: List[str]
    ports: List[str]
    volumes: List[str]


@dataclass
class Image:
    name: str
    digest: str
    old_digest: str = None


@dataclass
class ServiceDetails:
    status: ServiceStatus
    old: ServiceDef = None
    new: ServiceDef = None
    diff: List[str] = field(default_factory=list)
    image_pull: Image = None


@dataclass
class ImageDetails:
    name: str
    branch: str
    local: Optional[ImageMetadata]
    registry: Optional[ImageMetadata]

    @property
    def pull(self) -> Optional[Image]:
        if not self.local:
            if not self.registry:
                print("")
                raise RuntimeError("Image %s not found" % self.name)
            return Image(name="{}:{}".format(self.registry.repo, self.registry.tag), digest=self.registry.digest)
        else:
            if not self.registry:
                return None
            if self.local.digest != self.registry.digest:
                return Image(name="{}:{}".format(self.registry.repo, self.registry.tag), digest=self.registry.digest, old_digest=self.local.digest)
            else:
                return None


@dataclass
class UpdateDetails:
    services: Dict[str, ServiceDetails]
    images: Dict[str, ImageDetails]

    def _status_text(self, status):
        if status == ServiceStatus.UP_TO_DATE:
            return "\033[32mup-to-date"
        elif status == ServiceStatus.OUTDATED:
            return "\033[33moutdated"
        elif status == ServiceStatus.MISSING:
            return "\033[31mmissing"
        elif status == ServiceStatus.DISABLED:
            return "disabled"

    def _extract_digest(self, digest):
        digest = digest.replace("sha256:", "")
        digest = digest[:5]
        return digest

    def __str__(self):
        lines = []
        for name, service in self.services.items():
            status = self._status_text(service.status)
            lines.append(f"- \033[1mService %s: %s\033[0m" % (name, status))
            if service.image_pull is not None:
                if service.image_pull.old_digest:
                    old_digest = service.image_pull.old_digest
                    old_digest = self._extract_digest(old_digest)
                else:
                    old_digest = "n/a"

                new_digest = service.image_pull.digest
                new_digest = self._extract_digest(new_digest)

                lines.append(f"  * image: new version available (%s, %s -> %s)" % (service.image_pull.name, old_digest, new_digest))
            for aspect in service.diff:
                lines.append(f"  * {aspect}: changed")
        return "\n".join(lines)


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


def _pprint_images_metadata(metadata: Dict[str, ImageMetadata]) -> str:
    lines = []
    for key, value in metadata.items():
        lines.append("- %s (%s)" % (key, value.digest))
        lines.append("  revision: %s" % value.revision)
        lines.append("  application revision: %s" % value.application_revision)
        lines.append("  created at: %s" % value.created_at)
    return "\n".join(lines)


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
                branch_tag = _get_branch_tag(tag, branch)
                m = get_fn(repo, branch_tag)
                self.logger.debug("%s:%s metadata: %s", repo, branch_tag, m)
            if not m:
                m = get_fn(repo, tag)
                self.logger.debug("%s:%s metadata: %s", repo, tag, m)
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
                        self.logger.exception("Failed to fetch metadata of image %s", task)
                        failed.append((task, e))
                for f in not_done:
                    task = fs[f]
                    self.logger.error("Failed to fetch metadata of image %s (timeout)", task)
                    failed.append((task, TimeoutError()))
                tasks = []
                for image, exception in failed:
                    tasks.append(image)

                time.sleep(retry_delay)
        return result

    def _check_images(self, images: List[str], details: UpdateDetails):
        branch = self.node_manager.config.branch

        self.logger.debug("Update check for images: %s", ", ".join(images))

        local_metadata = self._fetch_metadata(images, branch, self.docker_template.get_local_image_metadata)
        registry_metadata = self._fetch_metadata(images, branch, self.docker_template.get_registry_image_metadata)

        # Update details
        for image in images:
            details.images[image] = ImageDetails(
                name=image,
                branch=branch,
                local=local_metadata.get(image, None),
                registry=registry_metadata.get(image, None),
            )

    def check_for_updates(self) -> Optional[UpdateDetails]:
        current_snapshot = self.node_manager.current_snapshot
        with open(current_snapshot) as f:
            current_snapshot = load(f, Loader=Loader)

        result = UpdateDetails(services={}, images={})
        images = set()
        for name, service in current_snapshot["services"].items():
            service = _parse_service_yaml(name, service)
            result.services[name] = ServiceDetails(
                status=ServiceStatus.UP_TO_DATE,
                new=service,
            )
            images.add(service.image)

        images = list(images)
        images = sorted(images)

        self._check_images(images, result)

        previous_snapshot = self.node_manager.previous_snapshot
        if previous_snapshot:
            with open(previous_snapshot) as f:
                previous_snapshot = load(f, Loader=Loader)
            for name, service in previous_snapshot["services"].items():
                if name in result.services:
                    s = result.services[name]
                    s.old = _parse_service_yaml(name, service)
                    # diff old and new service definitions
                    image_pull = result.images[s.new.image].pull
                    image_diff = s.old.image != s.new.image
                    command_diff = s.old.command != s.new.command
                    environment_diff = set(s.old.environment) != set(s.new.environment)
                    ports_diff = set(s.old.ports) != set(s.new.ports)
                    volumes_diff = set(s.old.volumes) != set(s.new.volumes)
                    if image_pull is not None or image_diff or command_diff or environment_diff or ports_diff or volumes_diff:
                        s.status = ServiceStatus.OUTDATED
                        s.image_pull = image_pull
                        if image_diff:
                            s.diff.append("image")
                        if command_diff:
                            s.diff.append("command")
                        if environment_diff:
                            s.diff.append("environment")
                        if ports_diff:
                            s.diff.append("ports")
                        if volumes_diff:
                            s.diff.append("volumes")
                else:
                    # old service is gone
                    result.services[name] = ServiceDetails(
                        status=ServiceStatus.DISABLED,
                        old=_parse_service_yaml(name, service)
                    )
        else:
            for s in result.services.values():
                image_pull = result.images[s.new.image].pull
                if image_pull is not None:
                    s.status = ServiceStatus.OUTDATED
                    s.image_pull = image_pull

        for name, s in result.services.items():
            if s.status != ServiceStatus.DISABLED:
                network = self.node_manager.config.network
                c = self.docker_template.get_container(f"{network}_{name}_1")
                if c is None:
                    s.status = ServiceStatus.MISSING


        # handle down/restart all missing case
        all_missing = True
        for service in result.services.values():
            if service.status != ServiceStatus.MISSING and len(service.diff) == 0:
                all_missing = False
                break
        for image in result.images.values():
            if image.pull is not None:
                all_missing = False
        if all_missing:
            network = self.node_manager.config.network
            for name, service in result.services.items():
                container_name = f"{network}_{name}_1"
                print(f"📦 Creating container {container_name}...")
                self.node_manager.get_node(name).create_container()
            return None

        up_to_date = True
        for service in result.services.values():
            if service.status != ServiceStatus.UP_TO_DATE:
                up_to_date = False
                break
        if up_to_date:
            return None

        return result

    def apply(self, updates: UpdateDetails) -> None:
        for name, image in updates.images.items():
            if image.pull is not None:
                pull_name = image.pull.name
                pull_digest = image.pull.digest
                try:
                    print("💿 Pulling image %s..." % pull_name)
                    repo, tag = pull_name.split(":")
                    self.docker_template.pull_image(repo, tag)
                    pulled_image = self.docker_template.get_image(pull_name)
                    assert pulled_image.id == pull_digest
                    if "__" in tag:
                        parts = tag.split("__")
                        tag = parts[0]
                        pulled_image.tag(repo, tag)
                except:
                    traceback.print_exc()
                    print("⚠️ Failed to pull %s" % pull_name)

        network = self.node_manager.config.network
        for name, service in updates.services.items():
            try:
                container_name = f"{network}_{name}_1"
                if service.status == ServiceStatus.MISSING:
                    print(f"📦 Creating container {container_name}...")
                    self.node_manager.get_node(name).create_container()
                elif service.status == ServiceStatus.DISABLED:
                    c = self.docker_template.get_container(container_name)
                    print(f"📦 Stopping container {container_name}...")
                    c.stop()
                    print(f"📦 Removing container {container_name}...")
                    c.remove()
                elif service.status == ServiceStatus.OUTDATED:
                    c = self.docker_template.get_container(container_name)
                    print(f"📦 Stopping container {container_name}...")
                    c.stop()
                    print(f"📦 Recreating container {container_name}...")
                    c.remove()
                    self.node_manager.get_node(name).create_container()
            except:
                traceback.print_exc()
                print("⚠️ Failed to update service %s" % name)
