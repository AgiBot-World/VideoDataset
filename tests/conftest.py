from __future__ import annotations

import importlib
import shutil
import subprocess

import pytest

try:
    from lerobot.datasets.lerobot_dataset import LeRobotDataset  # type: ignore

    from videodataset.dataset.lerobot_dataset import LeRobotVideoDataset
except ImportError:
    pass

from tests.utils.model import AdaptiveToyModel
from tests.utils.settings import dataset_settings


@pytest.fixture
def lerobot_check():
    """Check if lerobot is installed, skip if not."""
    if importlib.util.find_spec("lerobot") is None:
        pytest.skip("lerobot not installed, install with videodataset[lerobot]")


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


@pytest.fixture
def ucsd_kitchen_dataset(lerobot_check) -> LeRobotDataset:
    """Fixture to provide the SO101 stacking task dataset."""
    if dataset_settings.use_local_path:
        dataset = LeRobotDataset(
            repo_id=None,
            root=dataset_settings.lerobot_datasets_root_paths["ucsd_kitchen_dataset"],
        )
    else:
        dataset = LeRobotDataset(
            repo_id=dataset_settings.lerobot_datasets_repo_ids["ucsd_kitchen_dataset"],
            root=None,
        )
    return dataset


@pytest.fixture
def ucsd_kitchen_video_dataset(lerobot_check) -> LeRobotVideoDataset:
    """Fixture to provide the SO101 stacking task dataset with video."""
    if dataset_settings.use_local_path:
        dataset = LeRobotVideoDataset(
            repo_id=None,
            root=dataset_settings.lerobot_datasets_root_paths["ucsd_kitchen_dataset"],
        )
    else:
        dataset = LeRobotVideoDataset(
            repo_id=dataset_settings.lerobot_datasets_repo_ids["ucsd_kitchen_dataset"],
            root=None,
        )
    return dataset


@pytest.fixture
def adaptive_model() -> AdaptiveToyModel:
    """Fixture to initialize an toy model."""
    return AdaptiveToyModel()
