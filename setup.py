import os
import sys
import subprocess
from skbuild import setup

# 强制安装指定版本numpy
try:
    import numpy as np
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy==1.26.4"])
    import numpy as np

# 配置CMake参数
numpy_include = np.get_include()
os.environ["CMAKE_ARGS"] = " ".join(
    [
        "-DVIDEO_CODEC_SDK_PATH=/workspace/Video_Codec_SDK_12.1.14",
        "-DCUDA_TOOLKIT_ROOT_DIR=/usr/local/cuda",
        f"-DNUMPY_INCLUDE_DIR={numpy_include}",
    ]
)

setup(
    name="videodataset",
    version="0.3.0",
    packages=["videodataset", "videodataset.video_decoder"],
    package_dir={
        "videodataset": "src/videodataset",
        "videodataset.video_decoder": "src/videodataset/video_decoder",
    },
    package_data={"videodataset.video_decoder": ["*.so"]},
    cmake_install_dir="src/videodataset/video_decoder",
    include_package_data=True,
    cmake_args=[
        "-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={}".format(
            os.path.abspath("src/videodataset/video_decoder")
        )
    ],
    install_requires=[
        "numpy==1.26.4"  # 运行时依赖版本约束
    ],
)
