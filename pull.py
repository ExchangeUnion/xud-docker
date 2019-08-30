#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from subprocess import check_output
import sys
import os
import json
import threading
import logging

if sys.version_info[0] == 2:
    from urllib2 import Request, urlopen, HTTPError
else:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError

try:
    from subprocess import DEVNULL  # not available when python < 3.3
except ImportError:
    DEVNULL = open(os.devnull, 'wb')

REGISTRY = "registry.docker.io"
REGISTRY1 = "registry-1.docker.io"


class Image(object):
    def __init__(self, group, name, tag):
        self.group = group
        self.name = name
        self.tag = tag

    def __repr__(self):
        return "{}/{}:{}".format(self.group, self.name, self.tag)

    def __eq__(self, other):
        return self.group == other.group and self.name == other.name and self.tag == other.tag


class ImageNotFound(Exception):
    pass


class Service(object):
    def __init__(self, name):
        self.name = name
        self._image = None

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, value):
        parts = value.split('/')
        group = parts[0]
        parts = parts[1].split(':')
        name = parts[0]
        if len(parts) > 1:
            tag = parts[1]
        else:
            tag = 'latest'
        self._image = Image(group, name, tag)

    def __repr__(self):
        return "{}:{}".format(self.name, self.image)


def get_service_images():
    cmd = "cat docker-compose.yml | grep -A 999 services | grep -A 1 -E '^  [a-z]*:' | sed -E 's/ +//g' | sed -E 's/image://g' | sed -E '/--/d'"
    return check_output(cmd, shell=True).decode().splitlines()


def get_all_services():
    cmd = "cat docker-compose.yml | grep -A 999 services | sed -nE 's/^  ([a-z]+):$/\\1/p'"
    services = check_output(cmd, shell=True).decode().splitlines()
    return [Service(s) for s in services]


def load_services(network):
    os.chdir(os.path.expanduser("~/.xud-docker/" + network))
    services = get_all_services()
    images = get_service_images()
    for i in range(int(len(images) / 2)):
        name = images[i * 2][:-1]
        for s in services:
            if s.name == name:
                s.image = images[i * 2 + 1]
    return services


def get_local_image_metadata(image):
    cmd = "docker image inspect {}".format(image)
    try:
        text = check_output(cmd, shell=True, stderr=DEVNULL).decode().strip()
        return json.loads(text)[0]["Config"]
    except Exception as e:
        logging.debug("Failed to fetch the metadata of %s from local environment, reason: %s, %s", image, type(e), e)
        return None


def get_token(image):
    r = urlopen(
        "https://auth.docker.io/token?service={}&scope=repository:{}/{}:pull".format(REGISTRY, image.group, image.name))
    text = r.read()
    return json.loads(text)["token"]


def get_cloud_image_metadata(image):
    token = get_token(image)
    # TODO fetch image metadata from the registry of `docker info`
    req = Request("https://{}/v2/{}/{}/manifests/{}".format(REGISTRY1, image.group, image.name, image.tag))
    req.add_header("Authorization", "Bearer " + token)
    try:
        r = urlopen(req)
        text = r.read()
        j = json.loads(text)
        text = j["history"][0]["v1Compatibility"]
        j = json.loads(text)
        return j["config"]
    except HTTPError as e:
        if e.code == 404:
            return None
        else:
            raise ImageNotFound("{} {}", REGISTRY1, image)


def get_image_created_timestamp(metadata):
    try:
        return metadata["Labels"]["com.exchangeunion.image.created"]
    except:
        return "0000-00-00T00:00:00Z"


def get_image_digest(metadata):  # sha256
    try:
        return metadata["Image"]
    except:
        return ""


def get_cloud_image_metadata_with_branch(image, branch):
    if branch == 'master':
        return image, get_cloud_image_metadata(image)
    branch_image = Image(image.group, image.name, image.tag + "__" + branch.replace('/', '-'))
    m = get_cloud_image_metadata(branch_image)
    if m is None:
        return image, get_cloud_image_metadata(image)
    return branch_image, m


def get_pull_image(branch, image):

    m1 = get_local_image_metadata(image)
    remote_image, m2 = get_cloud_image_metadata_with_branch(image, branch)

    if m1 is None:
        if m2 is None:
            raise ImageNotFound(image)
        else:
            return remote_image
    else:
        if m2 is None:
            return None

    d1 = get_image_digest(m1)
    d2 = get_image_digest(m2)
    logging.debug("(%s) comparing digests\n    LOCAL:  (%s) %s\n    REMOTE: (%s) %s", image.name, image, d1, remote_image, d2)

    if d1 != d2:
        t1 = get_image_created_timestamp(m1)
        t2 = get_image_created_timestamp(m2)
        logging.debug("(%s) comparing created timestamps\n    LOCAL:  (%s) %s\n    REMOTE: (%s) %s", image.name, image, t1, remote_image, t2)

        if t1 < t2:
            return remote_image

    return None


def retag_image(image):
    nobranch = "{}".format(image).split("__")[0]
    cmd = "docker tag {} {}".format(image, nobranch)
    os.system(cmd)


def pull_image(image):
    print("Pulling {}".format(image))
    cmd = "docker pull {} >/dev/null 2>&1".format(image)
    os.system(cmd)
    if "__" in image.tag:
        retag_image(image)


def get_images(servies):
    result = []
    for s in servies:
        if len([x for x in result if x == s.image]) == 0:
            result.append(s.image)
    return result


def update(branch, image):
    try:
        result = get_pull_image(branch, image)
        if result is None:
            # print(image, "is up-to-date")
            pass
        else:
            pull_image(result)
    except ImageNotFound as e:
        logging.error("Image not found: %s", e)
        exit(1)


def update_images(branch, network):
    services = load_services(network)
    for image in get_images(services):
        t = threading.Thread(target=update, args=(branch, image))
        t.start()


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        eprint("Usage: {} <branch> <network>".format(sys.argv[0]))
        exit(1)
    branch = sys.argv[1]
    network = sys.argv[2]
    os.chdir(os.path.expanduser("~/.xud-docker/" + network))
    LOG_TIME = '%(asctime)s.%(msecs)03d'
    LOG_LEVEL = '%(levelname)5s'
    LOG_PID = '%(process)d'
    LOG_THREAD = '[%(threadName)15s]'
    LOG_LOGGER = '%(name)10s'
    LOG_MESSAGE = '%(message)s'
    LOG_FORMAT = '%s %s %s --- %s %s: %s' % (LOG_TIME, LOG_LEVEL, LOG_PID, LOG_THREAD, LOG_LOGGER, LOG_MESSAGE)
    logging.basicConfig(filename="xud-docker.log", filemode="w", format=LOG_FORMAT, level=logging.DEBUG)
    update_images(branch, network)
