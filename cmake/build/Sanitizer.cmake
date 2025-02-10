#[[
Copyright (C) 2018-2022 by George Cave - gcave@stablecoder.ca

Copyright (c) 2022, 2024 msclock - msclock@qq.com

Licensed under the Apache License, Version 2.0 (the "License"); you may not
use this file except in compliance with the License. You may obtain a copy of
the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations under
the License.

See https://github.com/StableCoder/cmake-scripts/blob/main/sanitizers.cmake.
]]

include_guard(GLOBAL)

include(${CMAKE_CURRENT_LIST_DIR}/../Common.cmake)

set(USE_SANITIZER_ASAN_FLAGS
    # MSVC
    "/fsanitize=address /Zi"
    # Clang 3.2+ use this version. The no-omit-frame-pointer option is optional.
    "-g -fsanitize=address -fno-omit-frame-pointer" "-g -fsanitize=address"
    CACHE STRING "Compile with Address sanitizer flags.")

set(USE_SANITIZER_MSAN_FLAGS
    # MSVC
    "/fsanitize=memory"
    # GNU/Clang
    "-g -fsanitize=memory -fno-omit-frame-pointer -fsanitize-memory-track-origins"
    # Optional: -fno-optimize-sibling-calls -fsanitize-memory-track-origins=2
    "-g -fsanitize=memory -fno-omit-frame-pointer"
    "-g -fsanitize=memory"
    CACHE STRING "Compile with Memory sanitizer flags.")

set(USE_SANITIZER_USAN_FLAGS # GNU/Clang
    "-g -fsanitize=undefined"
    CACHE STRING "Compile with Undefined Behaviour sanitizer flags.")

set(USE_SANITIZER_TSAN_FLAGS # GNU/Clang
    "-g -fsanitize=thread"
    CACHE STRING "Compile with Thread sanitizer flags.")

set(USE_SANITIZER_LSAN_FLAGS # GNU/Clang
    "-g -fsanitize=leak"
    CACHE STRING "Compile with Leak sanitizer flags.")

set(USE_SANITIZER_CFI_FLAGS # GNU/Clang
    "-g -fsanitize=cfi"
    CACHE STRING "Compile with Control Flow Integrity(CFI) sanitizer flags.")

set(USE_SANITIZER
    "Address,Undefined"
    CACHE STRING "Compile with sanitizer flags.")

set(USE_SANITIZER_SKIP_TARGETS_REGEXES
    ""
    CACHE STRING "Regexes to skip targets to sanitize.")

set(USE_SANITIZER_BLACKLIST_FILE
    ""
    CACHE STRING "Path to a blacklist file for Undefined sanitizer.")

set(USE_SANITIZER_EXTRA_FLAGS
    ""
    CACHE STRING "Extra flags to pass to the sanitizer. Default to empty.")

message(
  STATUS
    "Use sanitizer with USE_SANITIZER: ${USE_SANITIZER}
  Sanitizer Options:
    USE_SANITIZER: OFF, Address, Memory, Undefined, Thread, Leak, CFI, EnableMSVCAnnotations
    USE_SANITIZER_ASAN_FLAGS: ${USE_SANITIZER_ASAN_FLAGS}
    USE_SANITIZER_MSAN_FLAGS: ${USE_SANITIZER_MSAN_FLAGS}
    USE_SANITIZER_USAN_FLAGS: ${USE_SANITIZER_USAN_FLAGS}
    USE_SANITIZER_TSAN_FLAGS: ${USE_SANITIZER_TSAN_FLAGS}
    USE_SANITIZER_LSAN_FLAGS: ${USE_SANITIZER_LSAN_FLAGS}
    USE_SANITIZER_CFI_FLAGS: ${USE_SANITIZER_CFI_FLAGS}
    USE_SANITIZER_EXTRA_FLAGS: Extra flags to pass to the sanitizer. Default to empty.
    USE_SANITIZER_BLACKLIST_FILE: Path to a blacklist file for Undefined sanitizer. Default to empty.
    USE_SANITIZER_SKIP_TARGETS_REGEXES: Regexes to skip targets to sanitize. Default to enable all targets instrumented.
  Note:
    - Thread can not work with Address and Leak sanitizers.
    - Memory can not work with Address, Leak, and Thread sanitizers.")

message(
  VERBOSE
  "Multiple values are allowed with USE_SANITIZER, e.g. -DUSE_SANITIZER=Address,Leak but some
  sanitizers cannot be combined together, e.g.-DUSE_SANITIZER=Address,Memory
  will result in configuration error. The delimiter character is not required
  and -DUSE_SANITIZER=AddressLeak would work as well.

  You can add more flags to USE_SANITIZER_EXTRA_FLAGS referring to the sanitizer
  documentation <https://clang.llvm.org/docs/index.html>.

  Sanitizer provides the commands:

    sanitize_target(target) - add sanitizer flags to a target including copy sanitizer runtime.
")

string(TOLOWER "${USE_SANITIZER}" USE_SANITIZER)

if(NOT USE_SANITIZER)
  message(STATUS "Sanitizer disabled by USE_SANITIZER evaluates to false.")
endif()

string(
  SHA256
    _sanitizer_flags_hash
    "${USE_SANITIZER_ASAN_FLAGS}#${USE_SANITIZER_MSAN_FLAGS}#${USE_SANITIZER_USAN_FLAGS}#${USE_SANITIZER_TSAN_FLAGS}#${USE_SANITIZER_LSAN_FLAGS}#${USE_SANITIZER_CFI_FLAGS}#${USE_SANITIZER_EXTRA_FLAGS}#${USE_SANITIZER_BLACKLIST_FILE}"
)
if(NOT DEFINED CACHE{__SANITIZER_FLAGS_HASH} OR NOT __SANITIZER_FLAGS_HASH
                                                STREQUAL _sanitizer_flags_hash)
  set(__SANITIZER_FLAGS_HASH
      "${_sanitizer_flags_hash}"
      CACHE INTERNAL "Hash of sanitizer flags options")
  set(__SAN_AVAILABLE_FLAGS "")

  if(USE_SANITIZER MATCHES [[thread]] AND (USE_SANITIZER MATCHES [[address]]
                                           OR USE_SANITIZER MATCHES [[leak]]))
    message(
      FATAL_ERROR
        "Thread sanitizer can not work with Address or Leak sanitizers.")
  endif()

  if(USE_SANITIZER MATCHES [[memory(withorigins)?]]
     AND (USE_SANITIZER MATCHES [[address]]
          OR USE_SANITIZER MATCHES [[leak]]
          OR USE_SANITIZER MATCHES [[thread]]))
    message(
      FATAL_ERROR
        "Memory sanitizer with origins track can not work with Address, Leak, and Thread sanitizers."
    )
  endif()

  if(USE_SANITIZER MATCHES [[address]])
    message(VERBOSE "Testing with Address sanitizer")

    foreach(_flag ${USE_SANITIZER_ASAN_FLAGS})
      check_and_append_flag(FLAGS "${_flag}" TARGETS __SAN_AVAILABLE_FLAGS)
    endforeach()
  endif()

  if(USE_SANITIZER MATCHES [[memory(withorigins)?]])
    message(VERBOSE "Testing with Memory sanitizer with origins track")

    foreach(_flag ${USE_SANITIZER_MSAN_FLAGS})
      check_and_append_flag(FLAGS "${_flag}" TARGETS __SAN_AVAILABLE_FLAGS)
    endforeach()
  endif()

  if(USE_SANITIZER MATCHES [[undefined]])
    message(VERBOSE "Testing with Undefined Behaviour sanitizer")

    foreach(_flag ${USE_SANITIZER_USAN_FLAGS})
      check_and_append_flag(FLAGS "${_flag}" TARGETS __SAN_AVAILABLE_FLAGS)
    endforeach()

    if(EXISTS "${USE_SANITIZER_BLACKLIST_FILE}")
      append_variable("-fsanitize-blacklist=${USE_SANITIZER_BLACKLIST_FILE}"
                      __SAN_AVAILABLE_FLAGS)
    endif()
  endif()

  if(USE_SANITIZER MATCHES [[thread]])
    message(VERBOSE "Testing with Thread sanitizer")

    foreach(_flag ${USE_SANITIZER_TSAN_FLAGS})
      check_and_append_flag(FLAGS "${_flag}" TARGETS __SAN_AVAILABLE_FLAGS)
    endforeach()
  endif()

  if(USE_SANITIZER MATCHES [[leak]])
    message(VERBOSE "Testing with Leak sanitizer")

    foreach(_flag ${USE_SANITIZER_LSAN_FLAGS})
      check_and_append_flag(FLAGS "${_flag}" TARGETS __SAN_AVAILABLE_FLAGS)
    endforeach()
  endif()

  if(USE_SANITIZER MATCHES [[cfi]])
    message(VERBOSE "Testing with Control Flow Integrity(CFI) sanitizer")

    foreach(_flag ${USE_SANITIZER_CFI_FLAGS})
      check_and_append_flag(FLAGS "${_flag}" TARGETS __SAN_AVAILABLE_FLAGS)
    endforeach()
  endif()

  if(USE_SANITIZER_EXTRA_FLAGS)
    message(VERBOSE "Test with extra flags: ${USE_SANITIZER_EXTRA_FLAGS}")
    check_and_append_flag(FLAGS "${USE_SANITIZER_EXTRA_FLAGS}" TARGETS
                          __SAN_AVAILABLE_FLAGS)
  endif()

  flags_to_list(__SAN_AVAILABLE_FLAGS "${__SAN_AVAILABLE_FLAGS}")

  set(__SAN_AVAILABLE_FLAGS
      ${__SAN_AVAILABLE_FLAGS}
      CACHE INTERNAL "Sanitizer flags")
endif()

message(STATUS "Sanitizer final flags: ${__SAN_AVAILABLE_FLAGS}")

#[[
A function to copy sanitizer runtime when open ASAN flags on windows.Basically,
it copy clang_rt.asan*.dll to target location.

Arguments:
  target - a target added by add_library, add_executable instructions.
]]
function(copy_sanitizer_runtime target)
  if(NOT WIN32 OR NOT USE_SANITIZER)
    return()
  endif()

  if(CMAKE_SIZEOF_VOID_P EQUAL 8) # 64-bit build
    set(ASAN_ARCHITECTURE "x86_64")
    set(ASAN_LIBRARY_HINT_DIR $ENV{VCToolsInstallDir}/bin/Hostx64/x64)
  else()
    set(ASAN_ARCHITECTURE "i386")
    set(ASAN_LIBRARY_HINT_DIR $ENV{VCToolsInstallDir}/bin/Hostx86/x86)
  endif()

  if(CMAKE_BUILD_TYPE STREQUAL Debug)
    set(ASAN_LIBRARY_NAME "clang_rt.asan_dbg_dynamic-${ASAN_ARCHITECTURE}.dll")
  else()
    set(ASAN_LIBRARY_NAME "clang_rt.asan_dynamic-${ASAN_ARCHITECTURE}.dll")
  endif()

  set(LLVM_SYMBOLIZER_NAME "llvm-symbolizer.exe")

  set(CMAKE_INSTALL_SYSTEM_RUNTIME_LIBS ${ASAN_LIBRARY_NAME})
  find_file(
    ASAN_LIBRARY_SOURCE
    NAMES ${ASAN_LIBRARY_NAME} REQUIRED
    HINTS ${ASAN_LIBRARY_HINT_DIR} $ENV{LIBPATH}
    DOC "Clang AddressSanitizer runtime")

  find_file(
    LLVM_SYMBOLIZER_SOURCE
    NAMES ${LLVM_SYMBOLIZER_NAME} REQUIRED
    HINTS ${ASAN_LIBRARY_HINT_DIR} $ENV{LIBPATH}
    DOC "LLVM symbolizer executable")

  add_custom_command(
    COMMENT "Copying ${ASAN_LIBRARY_SOURCE} to $<TARGET_FILE_DIR:${target}>"
    MAIN_DEPENDENCY ${ASAN_LIBRARY_SOURCE}
    TARGET ${target} POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different ${ASAN_LIBRARY_SOURCE}
            $<TARGET_FILE_DIR:${target}>)

  add_custom_command(
    COMMENT "Copying ${LLVM_SYMBOLIZER_SOURCE} to $<TARGET_FILE_DIR:${target}>"
    MAIN_DEPENDENCY ${LLVM_SYMBOLIZER_SOURCE}
    TARGET ${target} POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different ${LLVM_SYMBOLIZER_SOURCE}
            $<TARGET_FILE_DIR:${target}>)
endfunction()

#[[
Sanitize a target.

Note:
  - Use USE_SANITIZER_SKIP_TARGETS_REGEXES to skip targets that match the regex.

]]
function(sanitize_target target)
  set(_opts)
  set(_single_opts)
  set(_multi_opts EXCLUDE_FLAGS INCLUDE_FLAGS)
  cmake_parse_arguments(PARSE_ARGV 0 arg "${_opts}" "${_single_opts}"
                        "${_multi_opts}")

  if(NOT USE_SANITIZER)
    return()
  endif()

  get_target_property(_target_type ${target} TYPE)

  if(_target_type STREQUAL "INTERFACE_LIBRARY")
    message(
      VERBOSE
      "Skipping target ${target} due to INTERFACE_LIBRARY by ${CMAKE_CURRENT_FUNCTION}, because it cannot be compiled directly."
    )
    return()
  endif()

  if(USE_SANITIZER_SKIP_TARGETS_REGEXES)
    foreach(regex ${USE_SANITIZER_SKIP_TARGETS_REGEXES})
      if(target MATCHES "${regex}")
        message(
          VERBOSE
          "Skipping target ${target} by ${CMAKE_CURRENT_FUNCTION} due to regex ${regex}"
        )
        return()
      endif()
    endforeach()
  endif()

  if(NOT DEFINED CACHE{__SAN_AVAILABLE_FLAGS})
    message(
      FATAL_ERROR
        "Sanitizer flags not defined. Please check your configuration.")
  endif()

  set(_san $CACHE{__SAN_AVAILABLE_FLAGS})

  if(NOT MSVC)
    set(FLAGS ${_san})
    foreach(sanitizer address memory undefined thread leak cfi)
      if("-fsanitize=${sanitizer}" IN_LIST _san)
        list(APPEND _links "-fsanitize=${sanitizer}")
      endif()
    endforeach()

    if(_links)
      set(LINKS ${_links})
    endif()
  else()
    # MSVC support
    if(NOT USE_SANITIZER MATCHES [[enablemsvcannotations]])
      # https://learn.microsoft.com/en-us/answers/questions/864574/enabling-address-sanitizer-results-in-error-lnk203
      # https://learn.microsoft.com/en-us/cpp/sanitizers/error-container-overflow?view=msvc-170
      set(DEFINITIONS _DISABLE_VECTOR_ANNOTATION _DISABLE_STRING_ANNOTATION)
    endif()

    set(FLAGS ${_san} /Zi /INCREMENTAL:NO)
    set(LINKS /INCREMENTAL:NO)
  endif()

  if(arg_INCLUDE_FLAGS)
    message(VERBOSE
            "Including flags: ${arg_INCLUDE_FLAGS} for target ${target}")
    foreach(_include_flag ${arg_INCLUDE_FLAGS})
      check_and_append_flag(FLAGS "${_include_flag}" TARGETS FLAGS QUOTELESS)
      check_and_append_flag(FLAGS "${_include_flag}" TARGETS LINKS QUOTELESS)
    endforeach()
    message(VERBOSE "Sanitize flags with included flags for ${target}:
    Sanitize compiling flags: ${FLAGS}
    Sanitize linking flags: ${LINKS}")
  endif()

  if(arg_EXCLUDE_FLAGS)
    message(VERBOSE
            "Excluding flags: ${arg_EXCLUDE_FLAGS} for target ${target}")
    foreach(_exclude_flag ${arg_EXCLUDE_FLAGS})
      list(REMOVE_ITEM FLAGS "${_exclude_flag}")
      list(REMOVE_ITEM LINKS "${_exclude_flag}")
    endforeach()
    message(VERBOSE "Sanitize flags with excluded flags for ${target}:
    Sanitize compiling flags: ${FLAGS}
    Sanitize linking flags: ${LINKS}")
  endif()

  message(VERBOSE "Sanitize target ${target} by ${CMAKE_CURRENT_FUNCTION}:
    Sanitize compiling flags: ${FLAGS}
    Sanitize linking flags: ${LINKS}")

  options_target(
    ${target}
    FLAGS
    ${FLAGS}
    LINKS
    ${LINKS}
    DEFINITIONS
    ${DEFINITIONS})

  copy_sanitizer_runtime(${target})
endfunction()
