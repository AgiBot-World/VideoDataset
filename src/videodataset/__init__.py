"""
Copyright (c) 2025 agibot. All rights reserved.

videodataset: Video Dataset with NvCodec.
"""

from __future__ import annotations

import importlib
import os
import platform


def _setup_environment():
    """Setup environment variables and paths"""
    if platform.system() == "Linux":
        # Linux: Update LD_LIBRARY_PATH
        lib_paths: list[str] = []

        # Add torch library path for _decoder extension
        try:
            torch = importlib.import_module("torch")
            lib_paths.append(os.path.dirname(torch.__file__) + "/lib")
        except ImportError:
            err_msg = "Unable to import torch. Please ensure torch is installed."
            raise ImportError(err_msg)

        if "LD_LIBRARY_PATH" in os.environ:
            lib_paths.extend(os.environ["LD_LIBRARY_PATH"].split(":"))

        os.environ["LD_LIBRARY_PATH"] = ":".join(filter(None, lib_paths))


_setup_environment()

from videodataset._decoder import VideoDecoder

__all__ = ["VideoDecoder"]
