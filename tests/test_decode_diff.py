from __future__ import annotations

import multiprocessing as mp
import os
from pathlib import Path

import cv2
import numpy as np
import pytest
import torch
from skimage.metrics import structural_similarity as ssim
from torch.utils.data import DataLoader, Dataset

from videodataset import VideoDecoder
from videodataset.utils.video_util import nv12_to_rgb


def mse(image1, image2):
    """Calculate the Mean Squared Error between two images.

    Args:
        image1 (np.ndarray): First image as NumPy array.
        image2 (np.ndarray): Second image as NumPy array.

    Returns:
        float: Mean Squared Error value.
    """
    return np.mean((image1 - image2) ** 2)


def psnr(image1, image2, max_pixel=255.0):
    """Calculate the Peak Signal-to-Noise Ratio between two images.

    Args:
        image1 (np.ndarray): First image as NumPy array.
        image2 (np.ndarray): Second image as NumPy array.
        max_pixel (float): Maximum possible pixel value of the images. Defaults to 255.0.

    Returns:
        float: PSNR value.
    """
    mse_value = np.mean((image1 - image2) ** 2)
    if mse_value == 0:
        return float("inf")
    return 20 * np.log10(max_pixel / np.sqrt(mse_value))


def calc_ssim(imageA, imageB):
    """Calculate the Structural Similarity Index between two images.

    Args:
        imageA (np.ndarray): First image as NumPy array.
        imageB (np.ndarray): Second image as NumPy array.

    Returns:
        float: SSIM value.
    """
    # Convert images to grayscale
    grayA = cv2.cvtColor(imageA, cv2.COLOR_BGR2GRAY)
    grayB = cv2.cvtColor(imageB, cv2.COLOR_BGR2GRAY)
    # Calculate SSIM
    return ssim(grayA, grayB)


def ms_ssim(image1, image2, max_val=255):
    """Calculate the Multi-Scale Structural Similarity Index between two images.

    Args:
        image1 (np.ndarray): First image as NumPy array.
        image2 (np.ndarray): Second image as NumPy array.
        max_val (int): Maximum possible pixel value of the images. Defaults to 255.

    Returns:
        float: MS-SSIM value.
    """
    levels = 5
    weights = np.array([0.0448, 0.2856, 0.3001, 0.2363, 0.1333])
    msssim = np.array([])
    for _ in range(levels):
        # Specify window size and channel axis
        sim = ssim(
            image1,
            image2,
            data_range=max_val,
            win_size=3,
            channel_axis=-1,
        )
        msssim = np.append(msssim, sim)
        image1 = cv2.resize(
            image1,
            (image1.shape[1] // 2, image1.shape[0] // 2),
            interpolation=cv2.INTER_AREA,
        )
        image2 = cv2.resize(
            image2,
            (image2.shape[1] // 2, image2.shape[0] // 2),
            interpolation=cv2.INTER_AREA,
        )
    return np.prod(msssim[0 : levels - 1] ** weights[0 : levels - 1]) * (
        msssim[levels - 1] ** weights[levels - 1]
    )


def get_sim_results(img1, img2):
    """Calculate similarity results between two images.

    Args:
        img1 (np.ndarray): First image as NumPy array.
        img2 (np.ndarray): Second image as NumPy array.

    Returns:
        dict: Dictionary containing the similarity results.
    """
    res = {}
    # res["mse"] = mse(img1, img2)
    # res["psnr"] = psnr(img1, img2)
    res["ssim"] = calc_ssim(img1, img2)
    # res['ms_ssim'] = ms_ssim(img1, img2)
    return res


class MyDataset(Dataset):
    """Custom dataset class for video decoding and comparison.

    Args:
        gpuid (int): GPU ID to use for decoding.
        data (list): List of data entries, each containing video file path, frame index, image file path, job ID, and episode ID.
        output_path (str): Directory path to save the comparison results.
    """

    def __init__(self, gpuid, data, output_path):
        self.codec = "h265"
        self.gpuid = gpuid
        self.decoder = None
        self.data = data
        self.output_path = output_path

    def __len__(self):
        """Get the number of data entries in the dataset.

        Returns:
            int: Number of data entries.
        """
        return len(self.data)

    def gray_image(self, img1, img2):
        """Convert two color images to grayscale and calculate their absolute difference.

        Args:
            img1 (np.ndarray): First image as NumPy array.
            img2 (np.ndarray): Second image as NumPy array.

        Returns:
            tuple: Tuple containing the two grayscale images and their absolute difference.
        """
        img1 = cv2.resize(img1, (img2.shape[1], img2.shape[0]))
        diff_color = cv2.absdiff(img1, img2)
        # diff_gray = cv2.cvtColor(diff_color, cv2.COLOR_BGR2GRAY)
        return img1, img2, diff_color

    def save_diff(self, img1, img2, diff, output_path):
        """Save the comparison result of two images and their difference.

        Args:
            img1 (np.ndarray): First image as NumPy array.
            img2 (np.ndarray): Second image as NumPy array.
            diff (np.ndarray): Absolute difference between the two images.
            output_path (str): File path to save the comparison result.
        """
        resized_images = []
        resized_images.append(img1)
        resized_images.append(img2)
        resized_images.append(diff)
        merged_image = np.hstack(resized_images)
        _ = cv2.imwrite(output_path, merged_image)

    def __getitem__(self, idx):
        """Get the similarity results for a specific frame in the dataset.

        Args:
            idx (int): Index of the data entry.

        Returns:
            dict: Dictionary containing the similarity results.

        Raises:
            Exception: If an error occurs during decoding or comparison.
        """
        if not self.decoder:
            self.decoder = VideoDecoder(self.gpuid, self.codec)
        try:
            data = self.data[idx]
            video = data["video"]
            idx = data["idx"]
            img = data["img"]
            job = data["job"]
            episode = data["episode"]
            decoded_frame = self.decoder.decode(video, int(idx))
            (height, width) = decoded_frame.shape
            src_tensor = torch.from_dlpack(decoded_frame)
            rgb_tensor = nv12_to_rgb(src_tensor, width, int(height / 1.5))
            rgb_tensor = rgb_tensor.cpu()
            np_image = rgb_tensor.numpy()
            np_image = np_image[:, :, [2, 1, 0]]
            img2 = cv2.imread(img)
            img1, img2, diff = self.gray_image(np_image, img2)
            output_path = f"{self.output_path}/{job}_{episode}_{idx}.jpg"
            self.save_diff(img1, img2, diff, output_path)
            return get_sim_results(img1, img2)
        except Exception as e:
            print(f"decode error:{idx}, {e}")
            raise e


def test_decode_diff():
    """Test the video decoding and comparison functionality.

    This function reads video and image data from a file, creates a dataset, and uses a DataLoader to process the data.
    It asserts that the SSIM values of the decoded and reference images are above a certain threshold.

    Raises:
        Exception: If the RANDOM_VIDEO_FILE environment variable is not set.
    """
    gpuid = 0
    random_video_file = os.environ.get("RANDOM_VIDEO_FILE", "")
    if not random_video_file:
        pytest.skip("RANDOM_VIDEO_FILE not set")

    output_dir = "output"

    data = []
    with Path(random_video_file).open() as f:
        for line in f.readlines():
            strip_line = line.strip()
            video, idx, img = strip_line.split(",")
            paths = video.split("/")
            job = paths[5]
            episode = paths[6]
            data.append(
                {"video": video, "idx": idx, "img": img, "job": job, "episode": episode}
            )

    dataset = MyDataset(gpuid, data, output_dir)

    spawn_ctx = mp.get_context("spawn")
    dataloader = DataLoader(
        dataset,
        batch_size=1,
        shuffle=True,
        num_workers=1,
        persistent_workers=True,
        drop_last=True,
        multiprocessing_context=spawn_ctx,
    )
    for batch in dataloader:
        ssim = batch["ssim"]
        epsilon = 1e-6
        is_all_above = torch.all(ssim > 0.7 - epsilon)
        assert is_all_above
