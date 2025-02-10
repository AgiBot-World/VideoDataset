#[[
This scripts setup a runpath properly when use add_library to generate
shared libraries or executables. The path will be pointed to lib or
executable directory by variable CMAKE_INSTALL_BIN. It also exports
some variables as below:
  - RUNPATH_SHARED_LOCATION: platform shared library location
  - RUNPATH_VCPKG_DPENDENCY_PATH: vcpkg library paths
  - RUNPATH_SYSTEM_DEPENDENCY_PATH: system paths
  - RUNPATH_DEPENDENCY_PATH: paths made of the above variables
]]

include_guard(GLOBAL)

# use, i.e. don't skip the full RPATH for the build tree
set(CMAKE_SKIP_BUILD_RPATH FALSE)

# add the automatically determined parts of the RPATH which point to directories
# outside the build tree to the install RPATH
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)

# Prepare RPATH
enable_language(C)
enable_language(CXX)
include(GNUInstallDirs)
file(RELATIVE_PATH _rel ${CMAKE_INSTALL_FULL_BINDIR}
     ${CMAKE_INSTALL_FULL_LIBDIR})
message(
  DEBUG
  "${CMAKE_INSTALL_FULL_BINDIR} relative to ${CMAKE_INSTALL_FULL_LIBDIR} path:${_rel}"
)

if(APPLE)
  set(_rpath "@loader_path/${_rel}")
  list(APPEND _rpath @loader_path)
else()
  set(_rpath "$ORIGIN/${_rel}")
  list(APPEND _rpath $ORIGIN)
endif()

# Append runtime path
list(APPEND CMAKE_INSTALL_RPATH ${_rpath})
message(STATUS "CMAKE_INSTALL_RPATH:${CMAKE_INSTALL_RPATH}")

# Skip RPATH for MinGW and Windows
foreach(_id C CXX)
  if(DEFINED CMAKE_${_id}_PLATFORM_ID
     AND ${CMAKE_${_id}_PLATFORM_ID} MATCHES "MinGW"
     OR WIN32)
    set(CMAKE_SKIP_RPATH TRUE)
  endif()
endforeach()

unset(_rpath)
unset(_rel)

# Add a variable about platform shared library location
set(RUNPATH_SHARED_LOCATION
    $<IF:$<PLATFORM_ID:Windows>,${CMAKE_INSTALL_BINDIR},${CMAKE_INSTALL_LIBDIR}>
)

# Set full dependency search path
set(RUNPATH_DEPENDENCY_PATH)

# Add a variable about vcpkg dependency path
if(VCPKG_INSTALLED_DIR AND VCPKG_TARGET_TRIPLET)
  set(RUNPATH_VCPKG_DPENDENCY_PATH
      ${VCPKG_INSTALLED_DIR}/${VCPKG_TARGET_TRIPLET}$<IF:$<CONFIG:Debug>,/deubg/${RUNPATH_SHARED_LOCATION},/${RUNPATH_SHARED_LOCATION}>
  )
endif()
list(APPEND RUNPATH_DEPENDENCY_PATH ${RUNPATH_VCPKG_DPENDENCY_PATH})

# Add dynamic libraries search path using system paths
if(DEFINED ENV{PATH})
  string(REPLACE "\\" "/" RUNPATH_SYSTEM_DEPENDENCY_PATH "$ENV{PATH}")
  list(APPEND RUNPATH_DEPENDENCY_PATH ${RUNPATH_SYSTEM_DEPENDENCY_PATH})
endif()
