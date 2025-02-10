from __future__ import annotations

import shutil
import subprocess

import pytest


@pytest.fixture
def ffmpeg_path():
    """Check FFmpeg availability and return path."""
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
