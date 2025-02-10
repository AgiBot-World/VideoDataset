#[[
This module provides some common tools.
]]

include_guard(GLOBAL)

#[[
Show project version friendly
]]
macro(show_project_version)
  message(STATUS "CMake Project Version:")
  message(STATUS "\tCMAKE_PROJECT_VERSION:${CMAKE_PROJECT_VERSION}")
  message(
    STATUS "\tCMAKE_PROJECT_VERSION_MAJOR: ${CMAKE_PROJECT_VERSION_MAJOR}")
  message(
    STATUS "\tCMAKE_PROJECT_VERSION_MINOR: ${CMAKE_PROJECT_VERSION_MINOR}")
  message(
    STATUS "\tCMAKE_PROJECT_VERSION_PATCH: ${CMAKE_PROJECT_VERSION_PATCH}")
  message(
    STATUS "\tCMAKE_PROJECT_VERSION_TWEAK: ${CMAKE_PROJECT_VERSION_TWEAK}")
endmacro()

#[[
Show vcpkg configurition
]]
function(show_vcpkg_configuration)
  # Print all vcpkg variables
  message(STATUS "Vcpkg Integration:")
  get_cmake_property(_vars VARIABLES)
  foreach(_var IN LISTS _vars)
    if(_var MATCHES "^VCPKG_")
      message(STATUS "\t${_var} ${${_var}}")
    endif()
  endforeach()
endfunction()

#[[
Add definition _DEBUG with config type Debug
]]
function(add_debug_macro)
  if(CMAKE_BUILD_TYPE STREQUAL Debug)
    add_definitions(-D_DEBUG)
    message(DEBUG "Ensure _DEBUG is defined for Debug configuration")
  endif()
endfunction()

#[[
A function to include directories to target.

Example:

  add_executable(main main.cpp)
  target_include_interface_directories(main include1 include2)

]]
function(target_include_interface_directories target)
  set(_includes)
  foreach(_include_dir ${ARGN})
    # Make include_dir absolute
    cmake_path(ABSOLUTE_PATH _include_dir BASE_DIRECTORY
               ${CMAKE_CURRENT_SOURCE_DIR})
    list(APPEND _includes $<BUILD_INTERFACE:${_include_dir}>)
  endforeach()

  list(APPEND _includes $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)
  # Include the interface directory
  get_target_property(_has_source_files ${target} SOURCES)
  if(NOT _has_source_files)
    target_include_directories(${target} INTERFACE ${_includes})
  else()
    target_include_directories(${target} PUBLIC ${_includes})
  endif()
endfunction()

#[[
A function to print a target's properties.

Example:

  print_target_properties(my_target)

]]
function(print_target_properties target)
  include(CMakePrintHelpers)
  # cmake-format: off
  cmake_print_properties(
    TARGETS ${target}
    PROPERTIES IMPORTED
               IMPORTED_COMMON_LANGUAGE_RUNTIME
               IMPORTED_CONFIGURATIONS
               IMPORTED_GLOBAL
               IMPORTED_IMPLIB
               IMPORTED_IMPLIB_Debug
               IMPORTED_IMPLIB_Release
               IMPORTED_LIBNAME
               IMPORTED_LIBNAME_Debug
               IMPORTED_LIBNAME_Release
               IMPORTED_LINK_DEPENDENT_LIBRARIES
               IMPORTED_LINK_DEPENDENT_LIBRARIES_Debug
               IMPORTED_LINK_DEPENDENT_LIBRARIES_Release
               IMPORTED_LINK_INTERFACE_LANGUAGES
               IMPORTED_LINK_INTERFACE_LANGUAGES_Debug
               IMPORTED_LINK_INTERFACE_LANGUAGES_Release
               IMPORTED_LINK_INTERFACE_LIBRARIES
               IMPORTED_LINK_INTERFACE_LIBRARIES_Debug
               IMPORTED_LINK_INTERFACE_LIBRARIES_Release
               IMPORTED_LINK_INTERFACE_MULTIPLICITY
               IMPORTED_LINK_INTERFACE_MULTIPLICITY_Debug
               IMPORTED_LINK_INTERFACE_MULTIPLICITY_Release
               IMPORTED_LOCATION
               IMPORTED_LOCATION_Debug
               IMPORTED_LOCATION_Release
               IMPORTED_NO_SONAME
               IMPORTED_NO_SONAME_Debug
               IMPORTED_NO_SONAME_Release
               IMPORTED_OBJECTS
               IMPORTED_OBJECTS_Debug
               IMPORTED_OBJECTS_Release
               IMPORTED_SONAME
               IMPORTED_SONAME_Debug
               IMPORTED_SONAME_Release
               IMPORT_PREFIX
               IMPORT_SUFFIX
               INCLUDE_DIRECTORIES
               INSTALL_NAME_DIR
               INSTALL_REMOVE_ENVIRONMENT_RPATH
               INSTALL_RPATH
               INSTALL_RPATH_USE_LINK_PATH
               INTERFACE_AUTOUIC_OPTIONS
               INTERFACE_COMPILE_DEFINITIONS
               INTERFACE_COMPILE_FEATURES
               INTERFACE_COMPILE_OPTIONS
               INTERFACE_INCLUDE_DIRECTORIES
               INTERFACE_LINK_DEPENDS
               INTERFACE_LINK_DIRECTORIES
               INTERFACE_LINK_LIBRARIES
               INTERFACE_LINK_OPTIONS
               INTERFACE_POSITION_INDEPENDENT_CODE
               INTERFACE_PRECOMPILE_HEADERS
               INTERFACE_SOURCES
               INTERFACE_SYSTEM_INCLUDE_DIRECTORIES
               LIBRARY_OUTPUT_DIRECTORY
               LIBRARY_OUTPUT_DIRECTORY_Debug
               LIBRARY_OUTPUT_DIRECTORY_Release
               LIBRARY_OUTPUT_NAME
               LIBRARY_OUTPUT_NAME_Debug
               LIBRARY_OUTPUT_NAME_Release
               LINK_DEPENDS
               LINK_DEPENDS_NO_SHARED
               LINK_DIRECTORIES
               LINK_FLAGS
               LINK_FLAGS_Debug
               LINK_FLAGS_Release
               LINK_INTERFACE_LIBRARIES
               LINK_INTERFACE_LIBRARIES_Debug
               LINK_INTERFACE_LIBRARIES_Release
               LINK_INTERFACE_MULTIPLICITY
               LINK_INTERFACE_MULTIPLICITY_Debug
               LINK_INTERFACE_MULTIPLICITY_Release
               LINK_LIBRARIES
               LINK_OPTIONS
               LOCATION
               LOCATION_Debug
               LOCATION_Release
               MANUALLY_ADDED_DEPENDENCIES
               MSVC_RUNTIME_LIBRARY
               NAME
               NO_SONAME
               NO_SYSTEM_FROM_IMPORTED
               OUTPUT_NAME
               OUTPUT_NAME_Debug
               OUTPUT_NAME_Release
               PCH_WARN_INVALID
               PCH_INSTANTIATE_TEMPLATES
               PDB_NAME
               PDB_NAME_Debug
               PDB_NAME_Release
               PDB_OUTPUT_DIRECTORY
               PDB_OUTPUT_DIRECTORY_Debug
               PDB_OUTPUT_DIRECTORY_Release
               PRECOMPILE_HEADERS
               PRECOMPILE_HEADERS_REUSE_FROM
               PREFIX
               PRIVATE_HEADER
               PUBLIC_HEADER
               RESOURCE
               RUNTIME_OUTPUT_DIRECTORY
               RUNTIME_OUTPUT_DIRECTORY_Debug
               RUNTIME_OUTPUT_DIRECTORY_Release
               RUNTIME_OUTPUT_NAME
               RUNTIME_OUTPUT_NAME_Debug
               RUNTIME_OUTPUT_NAME_Release
               SOURCE_DIR
               SOURCES
               STATIC_LIBRARY_FLAGS
               STATIC_LIBRARY_FLAGS_Debug
               STATIC_LIBRARY_FLAGS_Release
               STATIC_LIBRARY_OPTIONS
               SUFFIX
               TYPE
               VERSION
    )
    # cmake-format: on
endfunction()
