from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def tests_dir():
    """Get the directory of the tests."""
    return Path(__file__).parent


@pytest.fixture
def parent_dir(request):
    """Get the parent directory for test data.

    Priority:
    1. Use directory specified by TEST_DATA_DIR environment variable
    2. Fallback to the parent directory of the test file
    """
    parent_dir = os.environ.get("TEST_DATA_DIR")
    if parent_dir:
        return Path(parent_dir)
    return Path(__file__).parent


@pytest.fixture(scope="session")
def ffmpeg_path():
    """Check FFmpeg availability and return path"""
    path = shutil.which("ffmpeg")
    if not path:
        pytest.skip("FFmpeg not found in system PATH")
    return path


@pytest.fixture
def test_video(ffmpeg_path, tmp_path_factory):
    """Generate a test video using FFmpeg's test pattern source"""
    output_dir = tmp_path_factory.mktemp("test_videos")
    video_path = output_dir / "test_video.mp4"

    # FFmpeg command to generate a test video
    cmd = [
        ffmpeg_path,
        "-y",  # Overwrite output file without asking
        "-f",
        "lavfi",
        "-i",
        "mandelbrot=size=1280x720:rate=30",  # resolution, fps
        "-t",
        "1",  #  seconds
        "-c:v",
        "libx265",  # h265
        "-g",
        "8",  # GOP
        "-bf",
        "0",  # disable B frames
        "-pix_fmt",
        "yuv420p",  # Standard pixel format
        str(video_path),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Failed to generate test video: {e.stderr.decode()}")

    if not video_path.exists():
        pytest.fail("Test video was not created successfully")

    return video_path
