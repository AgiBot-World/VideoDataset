cmake_minimum_required(VERSION 3.15)
project(videodataset)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(CUDA REQUIRED)
set(CUDA_TOOLKIT_ROOT_DIR ${CUDA_TOOLKIT_ROOT_DIR})

find_package(Python REQUIRED COMPONENTS Interpreter Development)
find_package(pybind11 REQUIRED)
find_package(PkgConfig REQUIRED)

pkg_check_modules(FFMPEG REQUIRED
    libavformat
    libavcodec
    libavutil
    libswresample
)

include_directories(
    ${FFMPEG_INCLUDE_DIRS}
    ${CUDA_INCLUDE_DIRS}
    ${CMAKE_CURRENT_SOURCE_DIR}/include  # 关键路径修正
    ${CMAKE_CURRENT_SOURCE_DIR}/src
)

add_subdirectory(pybind)

install(TARGETS _decoder
    LIBRARY
    DESTINATION .
)
