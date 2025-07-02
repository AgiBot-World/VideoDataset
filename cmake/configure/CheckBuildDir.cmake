#[[
Check if the current directory is a source directory or a build directory.

Note:
  The configuration must be set after project().

If the current directory is a source directory, display an error message and terminate the build process.
If the current directory is a build directory, display a status message indicating that the build directory check passed.

Example Usage:

  include(CheckBuildDirectory)

Outputs:
- If the current directory is a source directory, a fatal error message is displayed.
- If the current directory is a build directory, a status message is displayed.
]]

file(TO_CMAKE_PATH "${PROJECT_BINARY_DIR}/CMakeLists.txt" _loc_path)

if(EXISTS "${_loc_path}")
  message(
    FATAL_ERROR
      "You cannot build in a source directory (or any directory with "
      "CMakeLists.txt file). Please make a build subdirectory. Feel free to "
      "remove CMakeCache.txt and CMakeFiles.")
else()
  message(STATUS "Build directory check passed")
endif()

unset(_loc_path)
