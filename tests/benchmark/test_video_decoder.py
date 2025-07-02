from __future__ import annotations

import pytest

from videodataset import VideoDecoder


def video_decode(video, frames: list):
    decoder = VideoDecoder(0, "h265")
    for index in frames:
        decoder.decode(str(video), index)


@pytest.mark.benchmark(group="block_decode")
@pytest.mark.parametrize(
    "block",
    [(0, 3), (3, 6), (6, 9)],
    ids=["block[0:3]", "block[3:6]", "block[6:9]"],
)
def test_decode_range(benchmark, test_video, block):
    benchmark.pedantic(
        video_decode,
        args=(test_video, block),
        iterations=4,
        rounds=10,
    )
