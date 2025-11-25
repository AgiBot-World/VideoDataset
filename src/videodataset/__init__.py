"""
Copyright (c) 2025 agibot. All rights reserved.

videodataset: A GPU-accelerated library that enables random frame access and efficient video decoding for data loading.
"""

from __future__ import annotations

import importlib
import os
import platform


def _setup_environment() -> None:
    """Setup environment variables and paths"""
    if platform.system() == "Linux":
        # Linux: Update LD_LIBRARY_PATH
        lib_paths: list[str] = []

        # Add torch library path for _decoder extension
        try:
            torch = importlib.import_module("torch")
            lib_paths.append(torch.__path__[0] + "/lib")
        except ImportError as e:
            err_msg = "Unable to import torch. Please ensure torch is installed."
            raise ImportError(err_msg) from e

        if "LD_LIBRARY_PATH" in os.environ:
            lib_paths.extend(os.environ["LD_LIBRARY_PATH"].split(":"))

        os.environ["LD_LIBRARY_PATH"] = ":".join(filter(None, lib_paths))


_setup_environment()

from videodataset._decoder import VideoDecoder  # noqa: E402

__all__ = ["VideoDecoder"]
