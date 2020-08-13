from __future__ import annotations

import time
import traceback
import os
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from enum import Enum
from logging import getLogger
from typing import Optional, Dict, List, TYPE_CHECKING
from datetime import datetime

from yaml import load

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

from .docker import DockerTemplate, ImageMetadata

if TYPE_CHECKING:
    from .NodeManager import NodeManager
    from launcher.config import Config
    from launcher.shell import Shell

__all__ = ["UpdateManager"]

logger = getLogger(__name__)


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
                return Image(name="{}:{}".format(self.registry.repo, self.registry.tag), digest=self.registry.digest,
                             old_digest=self.local.digest)
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

                lines.append(f"  * image: new version available (%s, %s -> %s)" % (
                service.image_pull.name, old_digest, new_digest))
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

    command = service.get("command", "")

    environment = service.get("environment", [])
    if not environment:
        environment = []
    environment = sorted(environment)

    ports = service.get("ports", [])
    if not ports:
        ports = []
    ports = sorted(ports)

    volumes = service.get("volumes", [])
    if not volumes:
        volumes = []
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
        self.node_manager = node_manager
        self.docker_template = DockerTemplate(node_manager.docker_client_factory)

        logs_dir = os.path.join(self.node_manager.config.network_dir, "logs")
        snapshots_dir = os.path.join(logs_dir, "snapshots")
        snapshots_dir = "/mnt/hostfs" + snapshots_dir
        self.snapshots_dir = snapshots_dir

        if not os.path.exists(snapshots_dir):
            os.makedirs(snapshots_dir)

        timestamp = int(datetime.now().timestamp())
        self.snapshot_file = os.path.join(self.snapshots_dir, f"snapshot-{timestamp}.yml")
        self.previous_snapshot_file = self._get_last_snapshot_file()

        if self.previous_snapshot_file:
            with open(self.previous_snapshot_file) as f:
                self.previous_snapshot = f.read()
        else:
            self.previous_snapshot = None

        self.current_snapshot = self.node_manager.export()

    def _get_last_snapshot_file(self) -> Optional[str]:
        snapshots = os.listdir(self.snapshots_dir)
        snapshots = sorted(snapshots)
        if len(snapshots) == 0:
            return None
        else:
            file = os.path.join(self.snapshots_dir, snapshots[-1])
            return file

    @property
    def config(self) -> Config:
        return self.node_manager.config

    @property
    def shell(self) -> Shell:
        return self.node_manager.shell

    def _fetch_metadata(self, images: List[str], branch: str, get_fn) -> Dict[str, ImageMetadata]:
        tasks = images

        def get_metadata(image: str) -> Optional[ImageMetadata]:
            repo, tag = image.split(":")
            m = None
            if get_fn == self.docker_template.get_registry_image_metadata:
                if branch != "master":
                    branch_tag = _get_branch_tag(tag, branch)
                    m = get_fn(repo, branch_tag)
                    logger.debug("%s:%s metadata: %s", repo, branch_tag, m)
            if not m:
                m = get_fn(repo, tag)
                logger.debug("%s:%s metadata: %s", repo, tag, m)
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
                        logger.exception("Failed to fetch metadata of image %s", task)
                        failed.append((task, e))
                for f in not_done:
                    task = fs[f]
                    logger.error("Failed to fetch metadata of image %s (timeout)", task)
                    failed.append((task, TimeoutError()))
                tasks = []
                for image, exception in failed:
                    tasks.append(image)

                time.sleep(retry_delay)
        return result

    def _check_images(self, images: List[str], details: UpdateDetails):
        branch = self.node_manager.config.branch

        logger.debug("Update check for images: %s", ", ".join(images))

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

    def _silent_update(self, updates: UpdateDetails) -> bool:
        image_outdated = False
        for image in updates.images.values():
            if image.pull is not None:
                image_outdated = True
        return self.node_manager.newly_installed or not image_outdated

    def update(self) -> str:
        if self.config.disable_update:
            self._persist_current_snapshot()
            return self.snapshot_file

        updates = self._check_for_updates()

        if self._silent_update(updates):
            if not self.node_manager.newly_installed:
                print("👍 All up-to-date.")
            self._persist_current_snapshot()
            self.node_manager.snapshot_file = self.snapshot_file
            self._apply(updates)
            return self.snapshot_file
        else:
            print(updates)
            answer = self.shell.yes_or_no(
                "Would you like to upgrade? (Warning: this may restart your environment and cancel all open orders)")
            if answer == "yes":
                self._persist_current_snapshot()
                self.node_manager.snapshot_file = self.snapshot_file
                self._apply(updates)
                return self.snapshot_file
            else:
                if self.previous_snapshot_file:
                    return self.previous_snapshot_file
                else:
                    self._persist_current_snapshot()
                    return self.current_snapshot

    def _check_for_updates(self) -> UpdateDetails:
        current_snapshot = load(self.current_snapshot, Loader=Loader)

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

        previous_snapshot = self.previous_snapshot
        if previous_snapshot:
            previous_snapshot = load(previous_snapshot, Loader=Loader)
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

        return result

    def _apply(self, updates: UpdateDetails) -> None:
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
                        tag0 = parts[0]
                        pulled_image.tag(repo, tag0)
                except:
                    traceback.print_exc()
                    print("⚠️ Failed to pull %s" % pull_name)

        network = self.node_manager.config.network
        for name, service in updates.services.items():
            try:
                container_name = f"{network}_{name}_1"
                if service.status == ServiceStatus.MISSING:
                    print(f"📦 Creating container {container_name}...")
                    self.node_manager.create(name)
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
                    self.node_manager.create(name)
            except:
                traceback.print_exc()
                print("⚠️ Failed to update service %s" % name)

    def _persist_current_snapshot(self):
        with open(self.snapshot_file, "w") as f:
            f.write(self.current_snapshot)
