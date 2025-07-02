#[[
Default to build.
]]
include_guard(GLOBAL)

set(CMAKE_EXPORT_COMPILE_COMMANDS
    ON
    CACHE BOOL "Generate compile_commands.json")

set(CMAKE_POSITION_INDEPENDENT_CODE
    ON
    CACHE BOOL "Always build position-independent code")

set(BUILD_SHARED_LIBS
    OFF
    CACHE
      BOOL
      "This will cause all libraries to be built shared unless the library was explicitly added as a static library.
This variable is often added to projects as an ``option()`` so that each user of a project can decide if they want
to build the project using shared or static libraries.")

include(${CMAKE_CURRENT_LIST_DIR}/Ccache.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/LinkOptimization.cmake)

# Source includes from vcpkg
if(VCPKG_INSTALLED_DIR AND VCPKG_TARGET_TRIPLET)
  include_directories(${VCPKG_INSTALLED_DIR}/${VCPKG_TARGET_TRIPLET}/include)
endif()
