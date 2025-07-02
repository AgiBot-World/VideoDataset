#[[
This module provides tools to handle cmake dependency installations painlessly.
]]

include_guard(GLOBAL)
include(${CMAKE_CURRENT_LIST_DIR}/Runpath.cmake)

if(WIN32 AND NOT ${CMAKE_HOST_SYSTEM_NAME} STREQUAL "Windows")
  # We're building for Windows on a different operating system. Set the platform
  # for get_runtime_dependencies() to "windows+pe"
  set(CMAKE_GET_RUNTIME_DEPENDENCIES_PLATFORM "windows+pe")
endif()

#[[
A function to enable installation of dependencies as part of the
 `make install` process.

Arguments:
  TARGETS - a list of installed targets to have dependencies copied for. (required)
  DIRECTORIES - directories to search dependencies. Default to ${RUNPATH_DEPENDENCY_PATH}. (optional)
  DEPENDS_DESTINATION - the runtime dependency installation directory for installed targets. Default to $<$<CONFIG:Debug>:debug/>${RUNPATH_SHARED_LOCATION}.(optional)
  PRE_EXCLUDE_REGEXES - regular expressions to handle results. (optional)
  POST_EXCLUDE_REGEXES - regular expressions to handle results. (optional)
  POST_INCLUDE_REGEXES - regular expressions to handle results. (optional)
  INSTALL_SYSTEM_LIBS - if present, all system libraries from include(InstallRequiredSystemLibraries) will be installed to ${DEPENDS_DESTINATION}. (optional)

Examples:
  set(app ${CMAKE_PROJECT_NAME}_app)

  add_library(shared SHARED shared.cpp)
  add_executable(${app} main.cpp)

  install(TARGETS ${app}
          RUNTIME DESTINATION $<$<CONFIG:Debug>:debug/>${CMAKE_INSTALL_BINDIR})
  install_dependency(TARGETS ${app})

Note:
  This requires CMake 3.14 for policy CMP0087
]]
function(install_dependency)
  if(CMAKE_VERSION VERSION_LESS "3.16")
    message(FATAL_ERROR "${CMAKE_CURRENT_FUNCTION} require at least CMake 3.16
(current version: ${CMAKE_VERSION})")
  endif()

  set(_opts INSTALL_SYSTEM_LIBS)
  set(_single_opts DEPENDS_DESTINATION)
  set(_multi_opts TARGETS DIRECTORIES PRE_EXCLUDE_REGEXES POST_EXCLUDE_REGEXES
                  POST_INCLUDE_REGEXES)
  cmake_parse_arguments(PARSE_ARGV 0 arg "${_opts}" "${_single_opts}"
                        "${_multi_opts}")

  if(DEFINED arg_UNPARSED_ARGUMENTS)
    message(
      FATAL_ERROR
        "${CMAKE_CURRENT_FUNCTION} was passed extra arguments: ${arg_UNPARSED_ARGUMENTS}"
    )
  endif()

  if(NOT DEFINED arg_DIRECTORIES)
    set(arg_DIRECTORIES ${RUNPATH_DEPENDENCY_PATH})
  endif()

  # Configure dependency installation destination
  if(NOT DEFINED arg_DEPENDS_DESTINATION)
    set(arg_DEPENDS_DESTINATION
        $<$<CONFIG:Debug>:debug/>${RUNPATH_SHARED_LOCATION})
  endif()

  if(IS_ABSOLUTE "${arg_DEPENDS_DESTINATION}")
    message(
      FATAL_ERROR
        "Must be relactive and invalid dependency destination: ${arg_DEPENDS_DESTINATION}"
    )
  endif()

  if(arg_INSTALL_SYSTEM_LIBS)
    # Configure system runtime dependency installation destination
    set(CMAKE_INSTALL_SYSTEM_RUNTIME_DESTINATION ${arg_DEPENDS_DESTINATION})

    # Include this module to search for compiler-provided system runtime
    # libraries and add install rules for them.
    include(InstallRequiredSystemLibraries)
    unset(CMAKE_INSTALL_SYSTEM_RUNTIME_DESTINATION)
  endif()

  set(arg_DEPENDS_DESTINATION
      "\${CMAKE_INSTALL_PREFIX}/${arg_DEPENDS_DESTINATION}")

  # Install CODE|SCRIPT allow the use of generator expressions
  cmake_policy(PUSH)

  # set CMP0087 install code for generator-expression
  if(POLICY CMP0048)
    cmake_policy(SET CMP0087 NEW)
  endif()

  list(APPEND arg_PRE_EXCLUDE_REGEXES "")
  list(APPEND arg_POST_EXCLUDE_REGEXES "")

  # Include debug shared system libs earlier
  if(CMAKE_BUILD_TYPE STREQUAL Debug)
    if(CMAKE_HOST_SYSTEM_NAME MATCHES [[Windows]])
      list(APPEND arg_POST_INCLUDE_REGEXES ".*d.dll")
    endif()
  endif()

  if(CMAKE_HOST_SYSTEM_NAME STREQUAL "Windows")
    # exclude common dll
    if(NOT arg_PRE_EXCLUDE_REGEXES)
      list(
        APPEND
        arg_PRE_EXCLUDE_REGEXES
        "api-ms-.*"
        "ext-ms-.*"
        "KERNEL32.*"
        "python.*"
        "msvcp.*"
        "vcruntime.*"
        "concrt.*")
    endif()

    # exclude system dlls directories later
    if(NOT arg_POST_EXCLUDE_REGEXES)
      list(APPEND arg_POST_EXCLUDE_REGEXES "WINDOWS" "system32")
    endif()
  else()
    # exclude system libs earlier
    if(NOT arg_PRE_EXCLUDE_REGEXES)
      list(
        APPEND
        arg_PRE_EXCLUDE_REGEXES
        "ld-linux[\.\-]"
        "libc[\.\-]"
        "libdl[\.\-]"
        "libdrm[\.\-]"
        "libelf[\.\-]"
        "libexpat[\.\-]"
        "libfontconfig[\.\-]"
        "libfreetype[\.\-]"
        "libg[\.\-]"
        "libgcc_s[\.\-]"
        "libGL[\.\-]"
        "libglib[\.\-]"
        "libgthread[\.\-]"
        "lib(ice|ICE)[\.\-]"
        "libnvidia[\.\-]"
        "libpthread[\.\-]"
        "libse(pol|linux)[\.\-]"
        "libSM[\.\-]"
        "libm[\.\-]"
        "librt[\.\-]"
        "libstdc[\+][\+][\.\-]"
        "libX[a-zA-Z0-9]*[\.\-]"
        "libxcb[\.\-]"
        "libutil[\.]")
    endif()

    # exclude system dlls directories later
    if(NOT arg_POST_EXCLUDE_REGEXES)
      list(APPEND arg_POST_EXCLUDE_REGEXES "x86_64-linux-gnu")
    endif()
  endif()

  if(CMAKE_HOST_SYSTEM_NAME MATCHES [[Linux]] AND EXISTS "/etc/alpine-release")
    find_program(_ldconfig ldconfig)
    execute_process(COMMAND ldconfig -v -N -X RESULT_VARIABLE ldconfig_result)

    if(NOT ldconfig_result EQUAL "0")
      message(STATUS "Patch ldconfig in alpine for GET_RUNTIME_DEPENDENCIES")
      file(READ "${_ldconfig}" _ldconfig_content)
      string(REPLACE [[[ $# -gt 0 ] && scan_dirs]]
                     [[[ $# -eq 0 ] && exit 0 || [ $# -gt 0 ] && scan_dirs]]
                     _ldconfig_content "${_ldconfig_content}")
      file(WRITE "${_ldconfig}" "${_ldconfig_content}")
    endif()
  endif()

  install(CODE "set(arg_DIRECTORIES \"${arg_DIRECTORIES}\")")
  install(CODE "set(arg_PRE_EXCLUDE_REGEXES \"${arg_PRE_EXCLUDE_REGEXES}\")")
  install(CODE "set(arg_POST_EXCLUDE_REGEXES \"${arg_POST_EXCLUDE_REGEXES}\")")
  install(CODE "set(arg_POST_INCLUDE_REGEXES \"${arg_POST_INCLUDE_REGEXES}\")")
  install(CODE "set(arg_DEPENDS_DESTINATION \"${arg_DEPENDS_DESTINATION}\")")

  foreach(target IN LISTS arg_TARGETS)
    get_target_property(target_type "${target}" TYPE)
    message(STATUS "target_type:${target_type};$<TARGET_FILE_NAME:${target}>")

    if(NOT target_type STREQUAL "INTERFACE_LIBRARY"
       AND NOT target_type STREQUAL "STATIC_LIBRARY")
      install(CODE "set(target_type \"${target_type}\")")
      install(CODE "set(target \"$<TARGET_FILE:${target}>\")")
      install(
        CODE [[

          if(NOT CMAKE_HOST_SYSTEM_NAME STREQUAL "Windows")
            set(file_install_param FOLLOW_SYMLINK_CHAIN)
          endif()

          set(library_target "")
          set(executable_target "")
          set(module_target "")
          if(target_type STREQUAL "SHARED_LIBRARY")
            set(library_target ${target})
          elseif(target_type STREQUAL "MODULE_LIBRARY")
            set(module_target ${target})
          elseif(target_type STREQUAL "EXECUTABLE")
            set(executable_target ${target})
          else()
            message(FATAL_ERROR "Unknown target type to resolve dependencies ${target_type}")
          endif()
          file(
            GET_RUNTIME_DEPENDENCIES
            EXECUTABLES
              ${executable_target}
            LIBRARIES
              ${library_target}
            MODULES
              ${module_target}
            RESOLVED_DEPENDENCIES_VAR
              _r_deps
            UNRESOLVED_DEPENDENCIES_VAR
              _u_deps
            CONFLICTING_DEPENDENCIES_PREFIX
              _c_deps
            DIRECTORIES
              ${arg_DIRECTORIES}
            PRE_EXCLUDE_REGEXES
              ${arg_PRE_EXCLUDE_REGEXES}
            POST_EXCLUDE_REGEXES
              ${arg_POST_EXCLUDE_REGEXES}
            POST_INCLUDE_REGEXES
              ${arg_POST_INCLUDE_REGEXES})

          if(_r_deps)
            message(STATUS "Resolved dependencies: ${_r_deps}")
            foreach(_file ${_r_deps})
              file(TO_CMAKE_PATH "${_file}" _file)
              message(STATUS "From ${_file}")
              file(
                INSTALL
                DESTINATION "${arg_DEPENDS_DESTINATION}"
                TYPE SHARED_LIBRARY ${file_install_param} FILES "${_file}")
            endforeach()
          endif()

          if(_u_deps)
            message(STATUS "Unresolved dependencies: ${_u_deps}")
            list(LENGTH _u_deps _u_length)
            if("${_u_length}" GREATER 0)
              message(WARNING "Unresolved dependencies detected:${_u_deps}")
            endif()
          endif()

          if(_c_deps)
            message(STATUS "Conflict dependencies: ${_c_deps_FILENAMES}")
            foreach(_filename ${_c_deps_FILENAMES})
              set(_c_file_list ${_c_deps_${_filename}})
              message(STATUS "conflict ${_filename} list ${_c_file_list}")
              foreach(_file ${_c_file_list})
                file(TO_CMAKE_PATH "${_file}" _file)
                message(STATUS "From ${_file}")
                file(
                  INSTALL
                  DESTINATION "${arg_DEPENDS_DESTINATION}"
                  TYPE SHARED_LIBRARY ${file_install_param} FILES "${_file}")
              endforeach()
            endforeach()
          endif()
          ]])
    endif()
  endforeach()

  cmake_policy(POP)
endfunction()
