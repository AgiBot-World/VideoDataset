set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/../../)

pybind11_add_module(_decoder
    ${CMAKE_CURRENT_SOURCE_DIR}/../src/video_decoder.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/bind.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../src/NvDecoder.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/../src/decoder_core.cpp
)

find_path(NVIDIA_SDK_DIR NAMES nvcuvid.h
    PATHS
    "$ENV{VIDEO_CODEC_SDK_PATH}"
    "/usr/local/nvidia/video_sdk"
    DOC "NVIDIA Video Codec SDK path"
)

target_include_directories(_decoder
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/../include  # 当前项目的头文件
        ${CUDA_INCLUDE_DIRS}
        ${FFMPEG_INCLUDE_DIRS}
        ${NVIDIA_SDK_DIR}/include
)

target_link_directories(_decoder
    PRIVATE
        ${CUDA_LIBRARY_DIRS}
        ${FFMPEG_LIBRARY_DIRS}
        ${NVIDIA_SDK_DIR}/lib
)

target_link_libraries(_decoder
    PRIVATE
        pybind11::module
        nvcuvid
        cuda
        nvidia-encode
        ${FFMPEG_LIBRARIES}
        avformat avcodec avutil swresample
)
