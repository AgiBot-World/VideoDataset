#[[
This file detects the git commit information and sets the version number accordingly.

Detected variables:
  - CMAKE_PROJECT_GIT_COMMIT_*: git commit information (see below)
  - CMAKE_PROJECT_VERSION: version number (major.minor.patch.tweak)
  - CMAKE_PROJECT_VERSION_<MAJOR|MINOR|PATCH|TWEAK>: version numbers (as integers)

]]

include_guard(GLOBAL)
include(configure/GitInfo)
include(configure/GitTools)
include(configure/ExtractVersion)

# Retrieve the git commit information to CMAKE_PROJECT_GIT_WT_* variables
git_wt_info(SOURCE_DIR ${CMAKE_SOURCE_DIR} PREFIX CMAKE_PROJECT)

# Rename CMAKE_PROJECT_GIT_WT_* variables to CMAKE_PROJECT_GIT_COMMIT_*
# variables
get_cmake_property(_vars VARIABLES)
foreach(_var IN LISTS _vars)
  if(_var MATCHES "^CMAKE_PROJECT_GIT_WT_")
    string(REGEX REPLACE "^CMAKE_PROJECT_GIT_WT_" "CMAKE_PROJECT_GIT_COMMIT_"
                         new_name "${_var}")
    set(${new_name} "${${_var}}")
    unset(new_name)
  endif()
endforeach()

# Set the CMAKE_PROJECT_VERSION variable
if(NOT CMAKE_PROJECT_GIT_COMMIT_TAG)
  set(CMAKE_PROJECT_VERSION "0.0.0.0")
else()
  set(CMAKE_PROJECT_VERSION "${CMAKE_PROJECT_GIT_COMMIT_TAG}")

  if(CMAKE_PROJECT_GIT_COMMIT_TAG_REVISION)
    set(CMAKE_PROJECT_VERSION
        "${CMAKE_PROJECT_VERSION}.${CMAKE_PROJECT_GIT_COMMIT_TAG_REVISION}")
  endif()

  string(REGEX REPLACE "^v" "" CMAKE_PROJECT_VERSION "${CMAKE_PROJECT_VERSION}")
endif()

# Set the CMAKE_PROJECT_VERSION_<MAJOR|MINOR|PATCH|TWEAK> variables
extract_version(CMAKE_PROJECT CMAKE_PROJECT REVERSE_NAME)
