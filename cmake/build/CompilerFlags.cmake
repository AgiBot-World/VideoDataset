#[[
This module provides tools to check and configure compiler options for targets.

See https://github.com/lefticus/cppbestpractices/blob/master/02-Use_the_Tools_Available.md for more information.
]]

include_guard(GLOBAL)

include(${CMAKE_CURRENT_LIST_DIR}/../Common.cmake)

set(COMPILER_FLAGS_WARNINGS_MSVC
    /W4 # Baseline reasonable warnings
    /w14242 # 'identifier': conversion from 'type1' to 'type2', possible loss of
            # data
    /w14254 # 'operator': conversion from 'type1:field_bits' to
            # 'type2:field_bits', possible loss of data
    /w14263 # 'function': member function does not override any base class
            # virtual member function
    /w14265 # 'classname': class has virtual functions, but destructor is not
            # virtual instances of this class may not be destructed correctly
    /w14287 # 'operator': unsigned/negative constant mismatch
    /we4289 # nonstandard extension used: 'variable': loop control variable
            # declared in the for-loop is used outside the for-loop scope
    /w14296 # 'operator': expression is always 'boolean_value'
    /w14311 # 'variable': pointer truncation from 'type1' to 'type2'
    /w14545 # expression before comma evaluates to a function which is missing
            # an argument list
    /w14546 # function call before comma missing argument list
    /w14547 # 'operator': operator before comma has no effect; expected operator
            # with side-effect
    /w14549 # 'operator': operator before comma has no effect; did you intend
            # 'operator'?
    /w14555 # expression has no effect; expected expression with side- effect
    /w14619 # pragma warning: there is no warning number 'number'
    /w14640 # Enable warning on thread un-safe static member initialization
    /w14826 # Conversion from 'type1' to 'type2' is sign-extended. This may
            # cause unexpected runtime behavior.
    /w14905 # wide string literal cast to 'LPSTR'
    /w14906 # string literal cast to 'LPWSTR'
    /w14928 # illegal copy-initialization; more than one user-defined conversion
            # has been implicitly applied
    /permissive- # standards conformance mode for MSVC compiler.
    CACHE STRING "Compiler warnings flags for MSVC")

set(COMPILER_FLAGS_WARNINGS_GNU
    -Wall # all warnings on
    -Wextra # reasonable and standard
    -Wshadow # warn the user if a variable declaration shadows one from a parent
             # context
    -Wnon-virtual-dtor # warn the user if a class with virtual functions has a
                       # non-virtual destructor. This helps catch hard to track
                       # down memory errors
    -Wold-style-cast # warn for c-style casts
    -Wcast-align # warn for potential performance problem casts
    -Wunused # warn on anything being unused
    -Woverloaded-virtual # warn if you overload (not override) a virtual
                         # function
    -Wpedantic # warn if non-standard C++ is used
    -Wconversion # warn on type conversions that may lose data
    -Wsign-conversion # warn on sign conversions
    -Wnull-dereference # warn if a null dereference is detected
    -Wdouble-promotion # warn if float is implicit promoted to double
    -Wformat=2 # warn on security issues around functions that format output (ie
               # printf)
    -Wimplicit-fallthrough # warn on statements that fallthrough without an
                           # explicit annotation
    # GCC specific
    -Wmisleading-indentation # warn if indentation implies blocks where blocks
                             # do not exist
    -Wduplicated-cond # warn if if / else chain has duplicated conditions
    -Wduplicated-branches # warn if if / else branches have duplicated code
    -Wlogical-op # warn about logical operations being used where bitwise were
                 # probably wanted
    -Wuseless-cast # warn if you perform a cast to the same type
    -Wsuggest-override # warn if an overridden member function is not marked
                       # 'override' or 'final'
    CACHE STRING "Compiler warnings flags for GNU")

set(COMPILER_FLAGS_WARNINGS_CUDA
    -Wall # Wall all warnings
    -Wextra # Reasonable and standard extra warnings
    -Wunused # Warn on anything being unused
    -Wconversion # Warn on type conversions that may lose data"
    -Wshadow # Warn the user if a variable declaration shadows one from a parent
             # context
    CACHE STRING "Compiler warnings flags for CUDA")

if(CMAKE_VERSION VERSION_LESS 3.24)
  option(CMAKE_COMPILE_WARNING_AS_ERROR "Treat Warnings As Errors" OFF)
endif()

set(COMPILER_FLAGS_SKIP_TARGETS_REGEXES
    ""
    CACHE STRING "List of regexes to skip targets.")

message(
  STATUS
    "Use Compiler flags:
  Compiler Flags Options:
    COMPILER_FLAGS_WARNINGS_MSVC: ${COMPILER_FLAGS_WARNINGS_MSVC}
    COMPILER_FLAGS_WARNINGS_GNU: ${COMPILER_FLAGS_WARNINGS_GNU}
    COMPILER_FLAGS_WARNINGS_CUDA: ${COMPILER_FLAGS_WARNINGS_CUDA}
    CMAKE_COMPILE_WARNING_AS_ERROR: If treat warnings as errors. Default is ${CMAKE_COMPILE_WARNING_AS_ERROR}.
    COMPILER_FLAGS_SKIP_TARGETS_REGEXES: List of regexes to skip targets. Default is empty."
)

string(
  SHA256
    _compiler_flags_hash
    "${COMPILER_FLAGS_WARNINGS_MSVC}#${COMPILER_FLAGS_WARNINGS_GNU}#${COMPILER_FLAGS_WARNINGS_CUDA}#${CMAKE_COMPILE_WARNING_AS_ERROR}"
)
if(NOT DEFINED CACHE{__COMPILER_FLAGS_HASH} OR NOT __COMPILER_FLAGS_HASH
                                               STREQUAL _compiler_flags_hash)
  set(__COMPILER_FLAGS_HASH
      "${_compiler_flags_hash}"
      CACHE INTERNAL "Hash of compiler flags options")
  set(__COMPILER_WARNINGS_C "")
  set(__COMPILER_WARNINGS_CXX "")
  set(__COMPILER_WARNINGS_CUDA "")

  if(MSVC)
    set(_warnings_cxx_temp ${COMPILER_FLAGS_WARNINGS_MSVC})
  elseif(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" OR CMAKE_CXX_COMPILER_ID MATCHES
                                                 ".*Clang")
    set(_warnings_cxx_temp ${COMPILER_FLAGS_WARNINGS_GNU})
  else()
    message(
      AUTHOR_WARNING
        "No compiler warnings set for CXX compiler: '${CMAKE_CXX_COMPILER_ID}'")
  endif()

  message(VERBOSE "Check Compiler Warnings CXX: ${_warnings_cxx_temp}")

  foreach(_warn ${_warnings_cxx_temp})
    check_and_append_flag(FLAGS "${_warn}" TARGETS __COMPILER_WARNINGS_CXX)
  endforeach()

  unset(_warnings_cxx_temp)

  if(CMAKE_COMPILE_WARNING_AS_ERROR)
    if(MSVC)
      check_and_append_flag(FLAGS "/WX" TARGETS __COMPILER_WARNINGS_CXX)
    elseif(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" OR CMAKE_CXX_COMPILER_ID
                                                   MATCHES ".*Clang")
      check_and_append_flag(FLAGS "-Werror" TARGETS __COMPILER_WARNINGS_CXX)
    else()
      message(
        AUTHOR_WARNING
          "No compiler warnings as errors set for CXX compiler: '${CMAKE_CXX_COMPILER_ID}'"
      )
    endif()
  endif()

  # use the same warning flags for C
  set(__COMPILER_WARNINGS_C "${__COMPILER_WARNINGS_CXX}")

  foreach(_warn ${COMPILER_FLAGS_WARNINGS_CUDA})
    check_and_append_flag(FLAGS "${_warn}" TARGETS __COMPILER_WARNINGS_CUDA)
  endforeach()

  flags_to_list(__COMPILER_WARNINGS_C "${__COMPILER_WARNINGS_C}")
  flags_to_list(__COMPILER_WARNINGS_CXX "${__COMPILER_WARNINGS_CXX}")
  flags_to_list(__COMPILER_WARNINGS_CUDA "${__COMPILER_WARNINGS_CUDA}")
  set(__COMPILER_WARNINGS_C
      "${__COMPILER_WARNINGS_C}"
      CACHE INTERNAL "compiler warnings flags for C")
  set(__COMPILER_WARNINGS_CXX
      "${__COMPILER_WARNINGS_CXX}"
      CACHE INTERNAL "compiler warnings flags for CXX")
  set(__COMPILER_WARNINGS_CUDA
      "${__COMPILER_WARNINGS_CUDA}"
      CACHE INTERNAL "compiler warnings flags for CUDA")
endif()

message(STATUS "Compiler final warnings for C: $CACHE{__COMPILER_WARNINGS_C}")
message(
  STATUS "Compiler final warnings for CXX: $CACHE{__COMPILER_WARNINGS_CXX}")
message(
  STATUS "Compiler final warnings for CUDA: $CACHE{__COMPILER_WARNINGS_CUDA}")

#[[
Function to apply compiler warnings to a target.
]]
function(warn_target target)
  set(_opts)
  set(_single_opts)
  set(_multi_opts EXCLUDE_FLAGS INCLUDE_FLAGS)
  cmake_parse_arguments(PARSE_ARGV 0 arg "${_opts}" "${_single_opts}"
                        "${_multi_opts}")

  if(COMPILER_FLAGS_SKIP_TARGETS_REGEXES)
    foreach(regex ${COMPILER_FLAGS_SKIP_TARGETS_REGEXES})
      if(target MATCHES "${regex}")
        message(
          VERBOSE
          "Skipping ${target} by ${CMAKE_CURRENT_FUNCTION} due to regex: ${regex}"
        )
        return()
      endif()
    endforeach()
  endif()

  if(NOT DEFINED CACHE{__COMPILER_WARNINGS_C}
     OR NOT DEFINED CACHE{__COMPILER_WARNINGS_CXX}
     OR NOT DEFINED CACHE{__COMPILER_WARNINGS_CUDA})
    message(
      FATAL_ERROR
        "Compiler warnings not set. Please call 'include(${CMAKE_CURRENT_LIST_DIR}/CompilerFlags.cmake)'"
    )
  endif()

  set(_c $CACHE{__COMPILER_WARNINGS_C})
  set(_cxx $CACHE{__COMPILER_WARNINGS_CXX})
  set(_cuda $CACHE{__COMPILER_WARNINGS_CUDA})

  if(arg_INCLUDE_FLAGS)
    message(VERBOSE
            "Including flags: ${arg_INCLUDE_FLAGS} for target ${target}")
    foreach(_include_flag ${arg_INCLUDE_FLAGS})
      check_and_append_flag(FLAGS "${_include_flag}" TARGETS _c QUOTELESS)
      check_and_append_flag(FLAGS "${_include_flag}" TARGETS _cxx QUOTELESS)
      check_and_append_flag(FLAGS "${_include_flag}" TARGETS _cuda QUOTELESS)
    endforeach()
    message(
      VERBOSE
      "Compiler warnings flags with included flags for ${target}:
    Compiler Warnings for C: ${_c}
    Compiler Warnings for CXX: ${_cxx}
    Compiler Warnings for CUDA: ${_cuda}")
  endif()

  if(arg_EXCLUDE_FLAGS)
    message(VERBOSE
            "Excluding flags: ${arg_EXCLUDE_FLAGS} for target ${target}")
    foreach(_exclude_flag ${arg_EXCLUDE_FLAGS})
      list(REMOVE_ITEM _c "${_exclude_flag}")
      list(REMOVE_ITEM _cxx "${_exclude_flag}")
      list(REMOVE_ITEM _cuda "${_exclude_flag}")
    endforeach()
    message(
      VERBOSE
      "Compiler warnings flags with excluded flags for ${target}:
    Compiler Warnings for C: ${_c}
    Compiler Warnings for CXX: ${_cxx}
    Compiler Warnings for CUDA: ${_cuda}")
  endif()

  message(
    VERBOSE
    "Applying compiler warnings to target ${target} by ${CMAKE_CURRENT_FUNCTION}:
    Compiler Warnings for C: ${_c}
    Compiler Warnings for CXX: ${_cxx}
    Compiler Warnings for CUDA: ${_cuda}")

  options_target(
    ${target} FLAGS $<$<COMPILE_LANGUAGE:C>:${_c}> # C warnings
    $<$<COMPILE_LANGUAGE:CXX>:${_cxx}> # C++ warnings
    $<$<COMPILE_LANGUAGE:CUDA>:${_cuda}> # Cuda warnings
  )
endfunction()
