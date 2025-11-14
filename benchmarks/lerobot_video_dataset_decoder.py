import argparse
import logging
import random

import cv2
import numpy as np
from lerobot.datasets.lerobot_dataset import LeRobotDataset
from skimage.metrics import structural_similarity as ssim
from tqdm import tqdm

from videodataset.dataset.lerobot_dataset import LeRobotVideoDataset

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def mse(image1, image2):
    """
    Calculate the Mean Squared Error between two images
    :param image1: First image as NumPy array
    :param image2: Second image as NumPy array
    :return: Mean Squared Error value
    """
    return np.mean((image1 - image2) ** 2)


def calc_ssim(imageA, imageB):
    """
    Calculate the Structural Similarity Index between two images
    :param imageA: First image as NumPy array
    :param imageB: Second image as NumPy array
    :return: SSIM value
    """
    # Convert images to grayscale
    grayA = cv2.cvtColor(imageA, cv2.COLOR_BGR2GRAY)
    grayB = cv2.cvtColor(imageB, cv2.COLOR_BGR2GRAY)
    # Calculate SSIM
    return ssim(grayA, grayB)


def get_sim_results(img1, img2):
    res = {}
    res["mse"] = mse(img1, img2)
    res["ssim"] = calc_ssim(img1, img2)
    return res


def main(
    data_dir: str,
):
    lerobot_dataset = LeRobotDataset(
        repo_id=None,
        root=data_dir,
    )
    lerobot_video_dataset = LeRobotVideoDataset(
        repo_id=None,
        root=data_dir,
    )

    indices = list(range(len(lerobot_video_dataset)))
    random.seed(42)
    random.shuffle(indices)

    video_keys = [
        key for key in lerobot_dataset[0] if key.startswith("observation.images")
    ]

    mse = {}
    ssim = {}
    for video_key in video_keys:
        mse[video_key] = np.array([], dtype=np.float32)
        ssim[video_key] = np.array([], dtype=np.float32)

    for idx in tqdm(indices, desc="decode image", miniters=50):
        lerobot_data = lerobot_dataset[idx]
        lerobot_video_data = lerobot_video_dataset[idx]

        for video_key in video_keys:
            lerobot_image = lerobot_data.get(video_key).permute(1, 2, 0).cpu().numpy()
            lerobot_video_image = (
                lerobot_video_data.get(video_key).permute(1, 2, 0).cpu().numpy()
            )
            lerobot_image *= 255
            lerobot_video_image *= 255
            lerobot_image = lerobot_image.astype(np.uint8)
            lerobot_video_image = lerobot_video_image.astype(np.uint8)
            diff_result = get_sim_results(
                lerobot_image,
                lerobot_video_image,
            )
            mse[video_key] = np.append(mse[video_key], diff_result.get("mse"))
            ssim[video_key] = np.append(ssim[video_key], diff_result.get("ssim"))

    for video_key in video_keys:
        mean_mse = np.mean(mse[video_key])
        mean_ssim = np.mean(ssim[video_key])
        logger.info(
            "%s mean mse is %f, mean ssim is %f", video_key, mean_mse, mean_ssim
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Video Dataset Performance Benchmark")

    parser.add_argument("--data-dir", type=str, default="", help="Path to the dataset")
    args = parser.parse_args()
    main(**vars(args))
