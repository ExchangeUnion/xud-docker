#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from subprocess import check_output
import sys
import os
import json

if sys.version_info[0] == 2:
    from urllib2 import Request, urlopen
else:
    from urllib.request import Request, urlopen

import threading

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
    cmd = "cat docker-compose.yml | grep -A -1 services | grep -A 1 -E '^  [a-z]*:' | sed -E 's/ +//g' | sed -E 's/image://g' | sed -E '/--/d'"
    return check_output(cmd, shell=True).decode().splitlines()


def get_all_services():
    cmd = "cat docker-compose.yml | grep -A -1 services | sed -nE 's/^  ([a-z]+):$/\\1/p'"
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
    except:
        return None


def get_token(image):
    r = urlopen(
        "https://auth.docker.io/token?service={}&scope=repository:{}/{}:pull".format(REGISTRY, image.group, image.name))
    text = r.read()
    return json.loads(text)["token"]


def get_cloud_image_metadata(image):
    token = get_token(image)
    req = Request("https://{}/v2/{}/{}/manifests/{}".format(REGISTRY1, image.group, image.name, image.tag))
    req.add_header("Authorization", "Bearer " + token)
    try:
        r = urlopen(req)
        text = r.read()
        j = json.loads(text)
        text = j["history"][0]["v1Compatibility"]
        j = json.loads(text)
        return j["config"]
    except:
        return None


def get_image_created_timestamp(metadata):

    return metadata["Labels"]["com.exchangeunion.image.created"]


def get_image_digest(metadata):  # sha256
    return metadata["Image"]


def get_pull_image(branch, image):
    branch_image = Image(image.group, image.name, image.tag + "__" + branch)

    m1 = get_local_image_metadata(image)
    m2 = get_cloud_image_metadata(branch_image)

    if m2 is None:
        if branch != 'master':
            m2 = get_cloud_image_metadata(image)
        else:
            raise Exception("Image not found: {}".format(image))

    if m1 is None:
        if m2 is None:
            raise Exception("Image not found: {}".format(image))
        else:
            return m2

    d1 = get_image_digest(m1)
    d2 = get_image_digest(m2)

    if d1 != d2:
        t1 = get_image_created_timestamp(m1)
        t2 = get_image_created_timestamp(m2)

        if t1 < t2:
            return m2

    return None


def retag_image(image):
    nobranch = "{}".format(image).split("__")[0]
    cmd = "docker tag {} {}".format(image, nobranch)
    os.system(cmd)


def pull_image(image):
    print("Pulling {}".format(image))
    cmd = "docker pull {}".format(image)
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
    result = get_pull_image(branch, image)
    if result is None:
        print(image, "is up-to-date")
    else:
        pull_image(result)


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
    update_images(branch, network)
