#[[
Configure valgrind to check memcheck on testsuit

Note:
  - Valgrind requires enable the testing to run testsuit command, e.g. `ctest -T memcheck` or `ctest -C Debug -D ExperimentalMemCheck`.
  - Valgrind can not work with sanitizer. You should disable it before run valgrind on testsuits.

Example:

  include(Valgrind)

]]
include_guard(GLOBAL)

set(USE_VALGRIND
    OFF
    CACHE BOOL "use valgrind to check memory issues.")

set(USE_VALGRIND_OPTIONS
    --show-leak-kinds=all # show all possible leak.
    --gen-suppressions=all # gen suppress info automatically.
    --track-origins=yes # locates the original position.
    CACHE STRING "valgrind options.")

set(USE_VALGRIND_SUPPRESSION_FILE
    ""
    CACHE STRING "path to valgrind suppress config file.")

set(USE_VALGRIND_ENABLE_MEMCHECK
    ON
    CACHE BOOL "enable memory check with ctest command.")

message(
  STATUS
    "Use valgrind with USE_VALGRIND: ${USE_VALGRIND}
  Valgrind Options:
    USE_VALGRIND: If use valgrind to check memory issues. Default is ${USE_VALGRIND}.
    USE_VALGRIND_OPTIONS: valgrind options. Default is ${USE_VALGRIND_OPTIONS}.
    USE_VALGRIND_SUPPRESSION_FILE: path to valgrind suppress config file. Default is empty.
    USE_VALGRIND_ENABLE_MEMCHECK: enable memory check with ctest command, e.g. ctest -T memcheck. Default is ${USE_VALGRIND_ENABLE_MEMCHECK}.
  Note:
    - Valgrind can not work with sanitizer. You should disable it before run valgrind on testsuits."
)

if(NOT CMAKE_HOST_UNIX)
  message(STATUS "Disable valgrind on non-unix system")
  return()
endif()

if(NOT USE_VALGRIND)
  message(STATUS "Disable valgrind by USE_VALGRIND evaluates to false")
  return()
endif()

find_program(
  VALGRIND_COMMAND
  NAMES valgrind
  DOC "valgrind executable")

if(NOT VALGRIND_COMMAND)
  message(WARNING "No valgrind found, disable valgrind to check memory issues")
  return()
endif()

message(STATUS "Found valgrind: ${VALGRIND_COMMAND}")

if(USE_VALGRIND_SUPPRESSION_FILE)
  set(valgrind_suppress_command
      "--suppressions=${USE_VALGRIND_SUPPRESSION_FILE}")
endif()

string(REPLACE ";" " " _valgrind_option_str "${USE_VALGRIND_OPTIONS}")

set(VALGRIND_COMMAND_OPTIONS
    "${_valgrind_option_str} ${valgrind_suppress_command}"
    CACHE STRING "valgrind options" FORCE)

message(STATUS "Valgrind final options: ${VALGRIND_COMMAND_OPTIONS}")

if(USE_VALGRIND_ENABLE_MEMCHECK)
  message(
    VERBOSE
    "Enable memory check with ctest command for testsuit, e.g. ctest -C Debug -D ExperimentalMemCheck"
  )
  set(MEMORYCHECK_COMMAND_OPTIONS
      "${_valgrind_option_str}"
      CACHE STRING "memory check command options" FORCE)

  message(STATUS "Memory check options: ${MEMORYCHECK_COMMAND_OPTIONS}")

  if(USE_VALGRIND_SUPPRESSION_FILE)
    set(MEMORYCHECK_SUPPRESSION_FILE
        "${USE_VALGRIND_SUPPRESSION_FILE}"
        CACHE STRING "memory check suppressions file" FORCE)
    message(
      STATUS "Memory check suppressions file: ${MEMORYCHECK_SUPPRESSION_FILE}")
  endif()
endif()

unset(valgrind_suppress_command)
unset(_valgrind_option_str)
