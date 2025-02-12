import setuptools

from setuptools import setup

package_name = "video_dataset"

install_requires = [
    'pycuda==2025.1',
    'PyNvVideoCodec==1.0.2'
]

setup(
    name=package_name,
    version="1.0.0",
    description=
    'VideoDataset lets users load and use video dataset efficiently.',
    packages=setuptools.find_packages(exclude=['tests*']),
    entry_points={
    },
    install_requires=install_requires,
    python_requires='>=3.10',
)
