#[[
Configure clang-tidy for static analysis when compiling a C++ project.
]]

include_guard(GLOBAL)

set(USE_CLANGTIDY
    ON
    CACHE BOOL "Use clang-tidy for static analysis of C++ code")

set(USE_CLANGTIDY_OPTIONS
    -extra-arg=-Wno-unknown-warning-option
    -extra-arg=-Wno-ignored-optimization-argument
    -extra-arg=-Wno-unused-command-line-argument -p ${CMAKE_BINARY_DIR})

set(USE_CLANGTIDY_WARNINGS_AS_ERRORS
    OFF
    CACHE BOOL "Treat cppcheck warnings as errors")

message(
  STATUS
    "Use Clang-tidy with USE_CLANGTIDY: ${USE_CLANGTIDY}
  Clang-tidy Options:
    USE_CLANGTIDY: If use clang-tidy. Default is ON.
    USE_CLANGTIDY_OPTIONS: clang-tidy run options. Default is ${USE_CLANGTIDY_OPTIONS}
    USE_CLANGTIDY_WARNINGS_AS_ERRORS: If treat warnings as errors. Default is OFF."
)

if(NOT USE_CLANGTIDY)
  message(STATUS "Disable clang-tidy by USE_CLANGTIDY evaluates to false")
  return()
endif()

find_program(
  CLANGTIDY_COMMAND
  NAMES clang-tidy
  DOC "Path to clang-tidy executable")

if(NOT CLANGTIDY_COMMAND)
  message(WARNING "No clang-tidy found, disabling clang-tidy analysis")
  return()
endif()

set(CMAKE_CXX_CLANG_TIDY ${CLANGTIDY_COMMAND} ${USE_CLANGTIDY_OPTIONS})

# Add the standard to the clang-tidy options
if(NOT "${CMAKE_CXX_STANDARD}" STREQUAL "")
  if(MSVC)
    list(APPEND CMAKE_CXX_CLANG_TIDY -extra-arg=/std:c++${CMAKE_CXX_STANDARD})
  else()
    list(APPEND CMAKE_CXX_CLANG_TIDY -extra-arg=-std=c++${CMAKE_CXX_STANDARD})
  endif()
endif()

if(USE_CLANGTIDY_WARNINGS_AS_ERRORS)
  list(APPEND CMAKE_CXX_CLANG_TIDY -warnings-as-errors=*)
endif()

list(REMOVE_DUPLICATES CMAKE_CXX_CLANG_TIDY)
message(STATUS "Clang-tidy final command: ${CMAKE_CXX_CLANG_TIDY}")
