#[[
Enable tests in CMake, and use CTest module to create a ``BUILD_TESTING``
option to select whether to enable tests.

Note:
  Use the module has some requirements:
    - Being placed in front of test configuration instructions in cmake.
    - Being placed in the source directory root because ctest expects to
      find a test file in the build directory root.
]]

include_guard(GLOBAL)

# Prevent the module from being used in the wrong location
if(NOT CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
  message(
    FATAL_ERROR
      "This module should be in the project root directory and placed "
      "in front of any test configuration instructions in cmake")
endif()

# Include CTest module to enable testing support. It creates a ``BUILD_TESTING``
# option that selects whether to enable testing support (``ON`` by default).
include(CTest)

function(add_test_subdirectory src)
  cmake_path(ABSOLUTE_PATH src BASE_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR})
  message(STATUS "Adding tests from ${src}")
  add_subdirectory(${src})
endfunction()
