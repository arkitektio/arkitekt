"""Talking to an OCI registry: the little of the distribution API a release needs.

Images are pushed by docker. What docker cannot push is the release descriptor (see
:mod:`arkitekt_spec.release`): a JSON blob and the manifest that carries it. That is
two requests against an API every registry speaks, so it is done here over plain
HTTP rather than through another tool the user would have to install.

Credentials are the ones ``docker login`` stored. Nothing is asked for and nothing
is written.
"""

import base64
import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from arkitekt_spec.release import (
    OCI_MANIFEST_MEDIA_TYPE,
    ReleaseDescriptor,
    descriptor_digest,
    digest_of,
    dump_descriptor,
    load_descriptor,
    parse_repository,
    release_manifest,
)

#: What a manifest may come back as: a release is a manifest, an image usually an index.
MANIFEST_TYPES = ", ".join(
    [
        OCI_MANIFEST_MEDIA_TYPE,
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
    ]
)

#: Docker Hub answers the API on another host than the one its images are named by,
#: and files its credentials under a third.
_DOCKER_HUB_API = "registry-1.docker.io"
_DOCKER_HUB_CREDENTIALS = "https://index.docker.io/v1/"

_TIMEOUT_SECONDS = 60


class RegistryError(Exception):
    """A registry refused a request, or could not be reached."""

    def __init__(self, message: str, status: Optional[int] = None) -> None:
        super().__init__(message)
        #: The status the registry answered with, when it answered.
        self.status = status


@dataclass(frozen=True)
class Response:
    status: int
    headers: Mapping[str, str]
    body: bytes


class _KeepAuthorizationHome(urllib.request.HTTPRedirectHandler):
    """Follow a redirect without carrying the registry's token to another host.

    Registries hand blobs off to object storage by redirect, and storage refuses a
    request that brings an Authorization header it did not issue.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and urllib.parse.urlsplit(newurl).netloc != req.host:
            new.remove_header("Authorization")
        return new


def docker_credentials(registry: str) -> Optional[tuple[str, str]]:
    """The username and secret ``docker login`` stored for a registry, if any."""
    config_dir = os.environ.get("DOCKER_CONFIG") or os.path.join(
        os.path.expanduser("~"), ".docker"
    )
    try:
        with open(os.path.join(config_dir, "config.json")) as file:
            config: dict[str, Any] = json.load(file)
    except (OSError, ValueError):
        return None

    names = [registry, f"https://{registry}"]
    if registry == "docker.io":
        names = [_DOCKER_HUB_CREDENTIALS, "index.docker.io", *names]

    for name in names:
        helper = (config.get("credHelpers") or {}).get(name) or config.get("credsStore")
        if helper:
            found = _ask_credential_helper(helper, name)
            if found:
                return found
        entry = (config.get("auths") or {}).get(name) or {}
        if entry.get("auth"):
            username, _, secret = base64.b64decode(entry["auth"]).decode().partition(":")
            return username, secret
    return None


def _ask_credential_helper(helper: str, name: str) -> Optional[tuple[str, str]]:
    try:
        result = subprocess.run(
            [f"docker-credential-{helper}", "get"],
            input=name,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            check=False,
        )
        answer = json.loads(result.stdout) if result.returncode == 0 else {}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
    if answer.get("Username") and answer.get("Secret"):
        return answer["Username"], answer["Secret"]
    return None


@dataclass
class Repository:
    """One repository on one registry."""

    registry: str
    repository: str
    credentials: Optional[tuple[str, str]] = None
    _authorization: Optional[str] = field(default=None, repr=False)

    @classmethod
    def of(cls, reference: str) -> "Repository":
        """The repository a reference names, with the credentials docker has for it."""
        registry, repository = parse_repository(reference)
        return cls(registry, repository, docker_credentials(registry))

    @property
    def name(self) -> str:
        """The repository as an image reference starts: ``registry/repository``."""
        return f"{self.registry}/{self.repository}"

    def pinned(self, digest: str) -> str:
        """The reference of a manifest in this repository, by digest."""
        return f"{self.name}@{digest}"

    # -- reading ------------------------------------------------------------

    def has(self, reference: str) -> bool:
        """Whether a tag or digest exists here."""
        return self._manifest_request("HEAD", reference).status == 200

    def manifest_digest(self, reference: str) -> Optional[str]:
        """The digest of the manifest a tag names, or None if there is none."""
        response = self._manifest_request("GET", reference)
        if response.status == 404:
            return None
        return response.headers.get("docker-content-digest") or digest_of(response.body)

    def manifest(self, reference: str) -> Optional[dict[str, Any]]:
        """The manifest a tag or digest names, or None if there is none."""
        response = self._manifest_request("GET", reference)
        if response.status == 404:
            return None
        return json.loads(response.body)

    def release(self, tag: str) -> Optional[ReleaseDescriptor]:
        """The release a tag names, or None if the tag is missing or names an image."""
        digest = descriptor_digest(self.manifest(tag))
        if digest is None:
            return None
        blob = self._checked("GET", f"blobs/{digest}", expect=(200,)).body
        if digest_of(blob) != digest:
            raise RegistryError(f"{self.name} returned other bytes than {digest} names.")
        return load_descriptor(blob)

    # -- writing ------------------------------------------------------------

    def push_release(self, tag: str, descriptor: ReleaseDescriptor) -> str:
        """Push a descriptor under a tag; return the digest of the manifest carrying it."""
        blob = dump_descriptor(descriptor)
        self._push_blob(blob)
        manifest = json.dumps(release_manifest(blob)).encode()
        response = self._checked(
            "PUT",
            f"manifests/{tag}",
            body=manifest,
            headers={"Content-Type": OCI_MANIFEST_MEDIA_TYPE},
            expect=(201,),
        )
        return response.headers.get("docker-content-digest") or digest_of(manifest)

    def _push_blob(self, blob: bytes) -> None:
        digest = digest_of(blob)
        if self._request("HEAD", f"blobs/{digest}").status == 200:
            return
        started = self._checked("POST", "blobs/uploads/", expect=(202,))
        location = started.headers.get("location")
        if not location:
            raise RegistryError(f"{self.name} opened an upload without saying where to send it.")
        location = urllib.parse.urljoin(self._url(""), location)
        separator = "&" if "?" in location else "?"
        self._checked(
            "PUT",
            location + separator + urllib.parse.urlencode({"digest": digest}),
            body=blob,
            headers={"Content-Type": "application/octet-stream"},
            expect=(201,),
        )

    # -- transport ----------------------------------------------------------

    def _manifest_request(self, method: str, reference: str) -> Response:
        response = self._request(method, f"manifests/{reference}", headers={"Accept": MANIFEST_TYPES})
        if response.status not in (200, 404):
            raise self._refused(method, f"manifests/{reference}", response)
        return response

    def _checked(self, method: str, path: str, *, expect: tuple[int, ...], **kwargs: Any) -> Response:
        response = self._request(method, path, **kwargs)
        if response.status not in expect:
            raise self._refused(method, path, response)
        return response

    def _refused(self, method: str, path: str, response: Response) -> RegistryError:
        detail = response.body.decode(errors="replace").strip()[:300]
        hint = ""
        if response.status in (401, 403):
            hint = (
                f" Log in first (`docker login {self.registry}`) with an account that may "
                "push to it."
                if self.credentials is None
                else f" The account docker is logged in to {self.registry} with may not do this."
            )
        return RegistryError(
            f"{self.name} answered {response.status} to {method} {path.split('?')[0]}.{hint}"
            + (f"\n{detail}" if detail else ""),
            status=response.status,
        )

    def _url(self, path: str) -> str:
        host = _DOCKER_HUB_API if self.registry == "docker.io" else self.registry
        local = host.split(":")[0] in ("localhost", "127.0.0.1")
        return f"{'http' if local else 'https'}://{host}/v2/{self.repository}/{path}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[bytes] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Response:
        url = path if "://" in path else self._url(path)
        response = self._send(method, url, body, headers)
        if response.status == 401 and self._authorize(response.headers.get("www-authenticate", "")):
            response = self._send(method, url, body, headers)
        return response

    def _send(
        self, method: str, url: str, body: Optional[bytes], headers: Optional[Mapping[str, str]]
    ) -> Response:
        request = urllib.request.Request(url, data=body, method=method, headers=dict(headers or {}))
        if self._authorization:
            request.add_header("Authorization", self._authorization)
        opener = urllib.request.build_opener(_KeepAuthorizationHome)
        try:
            with opener.open(request, timeout=_TIMEOUT_SECONDS) as answer:
                return Response(answer.status, _lowered(answer.headers), answer.read())
        except urllib.error.HTTPError as error:
            return Response(error.code, _lowered(error.headers), error.read())
        except (urllib.error.URLError, OSError) as error:
            raise RegistryError(f"Could not reach {self.registry}: {error}") from error

    def _authorize(self, challenge: str) -> bool:
        """Answer a registry's challenge; False when there is nothing new to answer with."""
        scheme, _, rest = challenge.partition(" ")
        parameters = dict(re.findall(r'(\w+)="([^"]*)"', rest))

        if scheme.lower() == "basic":
            if self.credentials is None or self._authorization:
                return False
            self._authorization = "Basic " + _basic(self.credentials)
            return True

        if scheme.lower() != "bearer" or "realm" not in parameters:
            return False

        query = {key: parameters[key] for key in ("service", "scope") if key in parameters}
        request = urllib.request.Request(parameters["realm"] + "?" + urllib.parse.urlencode(query))
        if self.credentials is not None:
            request.add_header("Authorization", "Basic " + _basic(self.credentials))
        try:
            with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as answer:
                granted = json.loads(answer.read())
        except (urllib.error.URLError, OSError, ValueError):
            return False
        token = granted.get("token") or granted.get("access_token")
        authorization = f"Bearer {token}" if token else None
        if authorization is None or authorization == self._authorization:
            return False
        self._authorization = authorization
        return True


def _basic(credentials: tuple[str, str]) -> str:
    return base64.b64encode(":".join(credentials).encode()).decode()


def _lowered(headers: Any) -> dict[str, str]:
    return {key.lower(): value for key, value in headers.items()}
