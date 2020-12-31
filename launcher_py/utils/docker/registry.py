import json
import re
import threading
from datetime import datetime, timedelta, timezone
from http.client import HTTPResponse
from typing import Dict
from urllib.request import urlopen, Request

from .errors import TokenError
from .models import Token

__all__ = (
    "DockerRegistryClient"
)


class TokenStore:
    token_url: str
    _store: Dict[str, Token]
    _dt_pattern: re.Pattern
    _lock: threading.RLock

    def __init__(self, token_url: str):
        self.token_url = token_url
        self._store = {}
        self._dt_pattern = re.compile(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})\.(\d+)Z")
        self._lock = threading.RLock()

    def get(self, repo: str) -> str:
        self._lock.acquire()
        if repo not in self._store:
            token = self._get_token(repo)
            self._store[repo] = token
        else:
            token = self._store[repo]
            if token.expired_at.timestamp() < datetime.now().timestamp():
                token = self._get_token(repo)
                self._store[repo] = token
        self._lock.release()
        return token.value

    def _parse_datetime(self, dtstr: str) -> datetime:
        m = self._dt_pattern.match(dtstr)
        if not m:
            raise Exception("Failed to parse datetime: " + dtstr)

        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))
        hour = int(m.group(4))
        minute = int(m.group(5))
        second = int(m.group(6))
        microsecond = int(m.group(7)[:6])
        microsecond = "{:<06d}".format(microsecond)
        microsecond = int(microsecond)
        return datetime(year, month, day, hour, minute, second, microsecond, tzinfo=timezone.utc)

    def _get_token(self, repo: str) -> Token:
        try:
            r = urlopen(f"{self.token_url}?service=registry.docker.io&scope=repository:{repo}:pull")
            payload = json.load(r)
            expires_in = payload["expires_in"]  # 300
            assert isinstance(expires_in, int)
            issued_at = payload["issued_at"]  # 2020-11-20T11:26:26.200591076Z
            issued_at = self._parse_datetime(issued_at)
            return Token(repo=repo, value=payload["token"], expired_at=issued_at + timedelta(seconds=expires_in))
        except Exception as e:
            raise TokenError(repo) from e


class DockerRegistryClient:
    _tokens: TokenStore

    def __init__(self):
        self._tokens = TokenStore("https://auth.docker.io/token")
        self.registry_url = "https://registry-1.docker.io/v2"

    def get_manifest(self, repo: str, ref: str) -> HTTPResponse:
        req = Request(f"{self.registry_url}/{repo}/manifests/{ref}")
        req.add_header("Authorization", f"Bearer {self._tokens.get(repo)}")
        accept = [
            "application/vnd.docker.distribution.manifest.v2+json",
            "application/vnd.docker.distribution.manifest.list.v2+json",
            "application/vnd.docker.distribution.manifest.v1+json",
        ]
        req.add_header("Accept", ",".join(accept))
        return urlopen(req)

    def get_blob(self, repo: str, digest: str) -> HTTPResponse:
        req = Request(f"{self.registry_url}/{repo}/blobs/{digest}")
        req.add_header("Authorization", f"Bearer {self._tokens.get(repo)}")
        return urlopen(req)
