import json
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import http.client
import time

from errors import FatalError


class RegistryClient:
    def __init__(self, auth_url, registry_url):
        self.auth_url = auth_url
        self.registry_url = registry_url

    def get_token(self, repo):
        r = urlopen("{}/token?service=registry.docker.io&scope=repository:{}:pull".format(self.auth_url, repo))
        return json.loads(r.read().decode())["token"]

    def get_manifest(self, repo, tag):
        url = f"{self.registry_url}/v2/{repo}/manifests/{tag}"
        request = Request(url)
        request.add_header("Authorization", "Bearer " + self.get_token(repo))
        request.add_header("Accept", "application/vnd.docker.distribution.manifest.list.v2+json")
        try:
            for i in range(3):
                try:
                    r = urlopen(request)
                    payload = json.loads(r.read().decode())
                    return payload
                except http.client.IncompleteRead:
                    pass
                except HTTPError as e:
                    if e.code == 404:
                        return None
                    else:
                        raise
                time.sleep(1)
            raise FatalError("Failed to get manifest: {}:{} (tried 3 times)".format(repo, tag))
        except Exception as e:
            raise FatalError("Failed to get manifest: {}:{}".format(repo, tag)) from e

    def get_blob(self, repo, digest):
        url = f"{self.registry_url}/v2/{repo}/blobs/{digest}"
        request = Request(url)
        request.add_header("Authorization", "Bearer {}".format(self.get_token(repo)))
        r = urlopen(request)
        payload = json.loads(r.read().decode())
        return payload
