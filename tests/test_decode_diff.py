from __future__ import annotations

import multiprocessing as mp
import os

import cv2
import numpy as np
import pytest
import torch
from skimage.metrics import structural_similarity as ssim
from torch.utils.data import DataLoader, Dataset

from videodataset import VideoDecoder


def mse(image1, image2):
    """
    Calculate the Mean Squared Error between two images
    :param image1: First image as NumPy array
    :param image2: Second image as NumPy array
    :return: Mean Squared Error value
    """
    return np.mean((image1 - image2) ** 2)


def psnr(image1, image2, max_pixel=255.0):
    """
    Calculate the Peak Signal-to-Noise Ratio between two images
    :param image1: First image as NumPy array
    :param image2: Second image as NumPy array
    :param max_pixel: Maximum possible pixel value of the images
    :return: PSNR value
    """
    mse_value = np.mean((image1 - image2) ** 2)
    if mse_value == 0:
        return float("inf")
    return 20 * np.log10(max_pixel / np.sqrt(mse_value))


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
    score = ssim(grayA, grayB)
    return score


def ms_ssim(image1, image2, max_val=255):
    """
    Calculate the Multi-Scale Structural Similarity Index between two images
    :param image1: First image as NumPy array
    :param image2: Second image as NumPy array
    :param max_val: Maximum possible pixel value of the images
    :return: MS-SSIM value
    """
    levels = 5
    weights = np.array([0.0448, 0.2856, 0.3001, 0.2363, 0.1333])
    msssim = np.array([])
    for _ in range(levels):
        # Specify window size and channel axis
        sim = ssim(image1, image2, data_range=max_val, win_size=3, channel_axis=-1)
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
    res = {}
    # res["mse"] = mse(img1, img2)
    # res["psnr"] = psnr(img1, img2)
    res["ssim"] = calc_ssim(img1, img2)
    # res['ms_ssim'] = ms_ssim(img1, img2)
    return res


class MyDataset(Dataset):
    def __init__(self, gpuid, data, output_path):
        pass
        self.codec = "h265"
        self.gpuid = gpuid
        self.decoder = None
        self.data = data
        self.output_path = output_path

    def __len__(self):
        return len(self.data)

    def nv12_to_rgb(self, nv12_tensor, width, height):
        try:
            nv12_tensor = nv12_tensor.to(dtype=torch.float32)
            y_plane = nv12_tensor[:height, :width]
            uv_plane = (
                nv12_tensor[height : height + height // 2, :]
                .view(height // 2, width // 2, 2)
                .repeat_interleave(2, dim=0)
                .repeat_interleave(2, dim=1)
            )
            u_plane = uv_plane[:, :, 0] - 128
            v_plane = uv_plane[:, :, 1] - 128
            r = y_plane + 1.402 * v_plane
            g = y_plane - 0.344136 * u_plane - 0.714136 * v_plane
            b = y_plane + 1.772 * u_plane
            rgb_frame = torch.stack((r, g, b), dim=2).clamp(0, 255).byte()
            return rgb_frame
        except Exception as e:
            print(f"Error converting NV12 to RGB: {e}")
            raise e

    def gray_image(self, img1, img2):
        img1 = cv2.resize(img1, (img2.shape[1], img2.shape[0]))
        diff_color = cv2.absdiff(img1, img2)
        # diff_gray = cv2.cvtColor(diff_color, cv2.COLOR_BGR2GRAY)
        return img1, img2, diff_color

    def save_diff(self, img1, img2, diff, output_path):
        resized_images = []
        resized_images.append(img1)
        resized_images.append(img2)
        resized_images.append(diff)
        merged_image = np.hstack(resized_images)
        _ = cv2.imwrite(output_path, merged_image)

    def __getitem__(self, idx):
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
            rgb_tensor = self.nv12_to_rgb(src_tensor, width, int(height / 1.5))
            rgb_tensor = rgb_tensor.cpu()
            np_image = rgb_tensor.numpy()
            np_image = np_image[:, :, [2, 1, 0]]
            img2 = cv2.imread(img)
            img1, img2, diff = self.gray_image(np_image, img2)
            output_path = f"{self.output_path}/{job}_{episode}_{idx}.jpg"
            self.save_diff(img1, img2, diff, output_path)
            eval_results = get_sim_results(img1, img2)
            return eval_results
        except Exception as e:
            print(f"decode error:{idx}, {e}")
            raise e


def test_decode_diff():
    gpuid = 0
    random_video_file = os.environ.get("RANDOM_VIDEO_FILE", "")
    if not random_video_file:
        pytest.skip("RANDOM_VIDEO_FILE not set")

    output_dir = "output"

    data = []
    with open(random_video_file, "r") as f:
        for line in f.readlines():
            line = line.strip()
            video, idx, img = line.split(",")
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
