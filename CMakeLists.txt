cmake_minimum_required(VERSION 3.25)
message(STATUS "CMAKE VERSION:${CMAKE_VERSION}")

set(CMAKE_PROJECT_TOP_LEVEL_INCLUDES cmake/configure/ConanProvider.cmake)

project(
  videodataset
  LANGUAGES CXX C CUDA
  HOMEPAGE_URL "https://github.com/AgiBot-World/VideoDataset")

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")

include(ProjectDefault)
include(ConfigureVersion)

add_subdirectory(csrc)
