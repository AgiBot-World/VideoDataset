import setuptools
from setuptools import setup

package_name = "video_dataset"

setup(
    name=package_name,
    version="0.1.0",
    description="VideoDataset lets users load and use video dataset efficiently.",
    packages=setuptools.find_packages(exclude=["tests*"]),
    entry_points={},
    python_requires=">=3.10",
)
