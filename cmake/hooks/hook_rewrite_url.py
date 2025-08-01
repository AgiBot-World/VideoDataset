from __future__ import annotations

import os
from urllib.parse import urlsplit, urlunsplit

import conan.tools.files
from conan.tools.files import download, get

GITHUB_PROXY = os.environ.get("GITHUB_PROXY", "")


def rewrite(url):
    """Rewrite the url to speed up the download process."""
    if isinstance(url, list):
        return [rewrite(u) for u in url]

    if not isinstance(url, str):
        type_msg = "URL should be a string or a list of strings."
        raise TypeError(type_msg)

    parts = list(urlsplit(url))
    if GITHUB_PROXY and "github.com" in parts[1]:
        if not GITHUB_PROXY.startswith(("http://", "https://")):
            err_msg = "GITHUB_PROXY should start with http:// or https://"
            raise RuntimeError(err_msg)

        # Prepend the proxy server to the front of the URL.
        parts.insert(0, GITHUB_PROXY)

    return urlunsplit(parts)


def custom_get(
    conanfile,
    url,
    md5=None,
    sha1=None,
    sha256=None,
    destination=".",
    filename="",
    keep_permissions=False,
    pattern=None,
    verify=True,
    retry=None,
    retry_wait=None,
    auth=None,
    headers=None,
    strip_root=False,
):
    get(
        conanfile,
        rewrite(url),
        md5,
        sha1,
        sha256,
        destination,
        filename,
        keep_permissions,
        pattern,
        verify,
        retry,
        retry_wait,
        auth,
        headers,
        strip_root,
    )


def custom_download(
    conanfile,
    url,
    filename,
    verify=True,
    retry=None,
    retry_wait=None,
    auth=None,
    headers=None,
    md5=None,
    sha1=None,
    sha256=None,
):
    download(
        conanfile,
        rewrite(url),
        filename,
        verify,
        retry,
        retry_wait,
        auth,
        headers,
        md5,
        sha1,
        sha256,
    )


if conan.tools.files.get is not custom_get:
    conan.tools.files.get = custom_get
if conan.tools.files.download is not custom_download:
    conan.tools.files.download = custom_download
