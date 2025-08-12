from __future__ import annotations

import os
from urllib.parse import urlsplit

from conan import ConanFile  # type: ignore

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
        return f"{GITHUB_PROXY.rstrip('/')}/{url}"
    return url


def pre_source(conanfile: ConanFile):
    """
    Rewrite the URL of the source before to execute the source() method.

    Reference: https://docs.conan.io/2/reference/extensions/hooks.html
    """
    try:
        sources = conanfile.conan_data.get("sources", {})
        version_sources = sources.get(conanfile.version, {})
        url = version_sources.get("url")

        if url:
            conanfile.output.info(f"Patch the URL before source() method: {url}.")
            new_url = rewrite(url)
            conanfile.output.info(f"Rewritten URL: {new_url}")
            conanfile.conan_data["sources"][conanfile.version]["url"] = new_url
    except Exception as e:
        err_msg = f"An error occurred while patching the URL: {e}"
        conanfile.output.warning(err_msg)
