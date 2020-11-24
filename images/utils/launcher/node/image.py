from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait, Future
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, TYPE_CHECKING, Optional
from typing import List, Tuple
import logging

from launcher.docker import Image as _Image
from launcher.docker import Layer
from launcher.errors import FatalError

if TYPE_CHECKING:
    from .base import Node
    from launcher.config import Config
    from launcher.shell import Shell
    from launcher.docker import DockerUtility


@dataclass
class ImageMetadata:
    name: str
    digest: str
    revision: Optional[str]
    created_at: datetime


class ImageNotFound(Exception):
    pass


@dataclass
class Image:
    repo: str
    tag: Optional[str]
    digest: Optional[str]
    pull: Optional[str]
    use: Optional[str]
    nodes: List[Node]
    layers: List[Layer]

    @property
    def in_use(self) -> bool:
        for node in self.nodes:
            if node.mode == "native" and not node.disabled:
                return True
        return False

    @property
    def use_local(self) -> bool:
        for node in self.nodes:
            if node.node_config["use_local_image"]:
                return True
        return False

    @property
    def name(self) -> str:
        return f"{self.repo}:{self.tag}"


class ImageManager:
    config: Config
    shell: Shell
    dockerutil: DockerUtility

    _image: Dict[str, Image]

    def __init__(self, config: Config, shell: Shell, dockerutil: DockerUtility):
        self.config = config
        self.shell = shell
        self.dockerutil = dockerutil

        self._images: Dict[str, Image] = {}
        self._logger = logging.getLogger(__name__ + ".ImageManager")

    def get_image(self, name: str, node: Node) -> Image:
        canonical_name = self.dockerutil.parse_image_name(name)
        if name not in self._images:
            image = Image(
                repo=canonical_name.repo,
                tag=canonical_name.tag,
                digest=canonical_name.digest,
                pull=None,
                use=name,
                nodes=[node],
                layers=[]
            )
            self._images[name] = image
        else:
            image = self._images[name]
            if node not in image.nodes:
                image.nodes.append(node)
        return image

    @property
    def branch(self) -> str:
        return self.config.branch

    def _get_local_image(self, image: Image) -> Optional[_Image]:
        name = image.name

        if self.branch == "master":
            image = self.dockerutil.get_image(name, local=True)
        else:
            name_branch = name + "__" + self.branch.replace("/", "-")
            image = self.dockerutil.get_image(name_branch, local=True)
            if not image:
                image = self.dockerutil.get_image(name, local=True)

        return image

    def _get_cloud_image(self, image: Image) -> Optional[_Image]:
        name = image.name

        if self.branch == "master":
            image = self.dockerutil.get_image(name)
        else:
            name_branch = name + "__" + self.branch.replace("/", "-")
            image = self.dockerutil.get_image(name_branch)
            if not image:
                image = self.dockerutil.get_image(name)

        return image

    def _check_image(self, image: Image) -> Tuple[str, Optional[str]]:
        local = self._get_local_image(image)

        if image.use_local:
            if not local:
                raise ImageNotFound(image.name)
            self._logger.debug("[Update] Image %s: Use local version, no pull", image.name)
            image.digest = local.digest
            return local.name, None

        cloud = self._get_cloud_image(image)

        if not local and not cloud:
            raise ImageNotFound(image.name)

        if local and not cloud:
            self._logger.debug("[Update] Image %s: Local only, no pull", image.name)
            image.digest = local.digest
            return local.name, None

        if cloud:
            image.layers.extend(cloud.layers)

        if not local and cloud:
            self._logger.debug("[Update] Image %s: Local missing, pull (%s)", image.name, cloud.name)
            image.digest = cloud.digest
            return cloud.name, cloud.name

        if local.digest == cloud.digest:
            self._logger.debug("[Update] Image %s: Up-to-date, no pull", image.name)
            image.digest = local.digest
            return local.name, None
        else:
            self._logger.debug("[Update] Image %s: Local outdated, pull (%s)", cloud.name)
            image.digest = cloud.digest
            return cloud.name, cloud.name

    def check_for_updates(self) -> List[Image]:
        images = list(self._images.values())

        # images in use
        images = [image for image in images if image.in_use]

        result = []

        with ThreadPoolExecutor(max_workers=len(images), thread_name_prefix="pool") as executor:
            futs: Dict[Future, Image] = {executor.submit(self._check_image, image): image for image in images}
            while True:
                done, not_done = wait(futs, 30)
                for f in done:
                    image = futs[f]
                    try:
                        use, pull = f.result()
                        image.use = use
                        if pull:
                            image.pull = pull
                            result.append(image)
                    except ImageNotFound:
                        raise FatalError("Image %s not found on DockerHub" % image.name)
                if len(not_done) == 0:
                    break
                reply = self.shell.yes_or_no("Keep waiting?")
                if reply == "no":
                    raise FatalError("Cancelled image checking")

        return result

    def pull_images(self, images: List[Image]) -> None:
        for image in images:
            if not image.pull:
                continue

            prefix = "Pulling %s... " % image.pull
            print(prefix + "preparing", flush=True)

            layers = {layer.digest[7: 19]: LayerState(downloading=0, extracting=0) for layer in image.layers}

            n = len(image.layers)

            c1 = "\033[1A\033[K"

            def update(status, layer, percentage):
                if not layer:
                    line = prefix + status
                    print(c1 + line, flush=True)
                    return

                if status == "downloading":
                    layers[layer].downloading = percentage
                elif status == "extracting":
                    layers[layer].extracting = percentage

                downloading = 0
                extracting = 0
                for layer, state in layers.items():
                    downloading += 1.0 / n * state.downloading
                    extracting += 1.0 / n * state.extracting
                s1 = "%.2f%%" % (downloading * 100)
                s2 = "%.2f%%" % (extracting * 100)
                line = prefix + "downloading %-7s | extracting %-7s" % (s1, s2)
                print(c1 + line, flush=True)

            self.dockerutil.pull_image(image.pull, update)


@dataclass
class LayerState:
    downloading: float
    extracting: float
