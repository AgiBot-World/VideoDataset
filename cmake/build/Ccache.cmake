#[[
Configure ccache optimization for compiling.

Example:

  include(Ccache)

]]

include_guard(GLOBAL)

set(USE_CCACHE
    ON
    CACHE BOOL "use ccache to speed up compiling.")

message(STATUS "Use Ccache with USE_CCACHE: ${USE_CCACHE}
  Ccache Options:
    USE_CCACHE: If use ccache to speed up compiling. Default is ON.")

if(NOT USE_CCACHE)
  message(STATUS "Disable ccache by USE_CCACHE evaluates to false.")
  return()
endif()

find_program(
  CCACHE_COMMAND
  NAMES ccache
  DOC "ccache executable")

if(NOT CCACHE_COMMAND)
  message(STATUS "No ccache found, disable ccache optimization.")
  return()
endif()

set(CMAKE_C_COMPILER_LAUNCHER "${CCACHE_COMMAND}")
set(CMAKE_CXX_COMPILER_LAUNCHER "${CCACHE_COMMAND}")

# set_property(GLOBAL PROPERTY RULE_LAUNCH_COMPILE ccache)

# set_property(GLOBAL PROPERTY RULE_LAUNCH_LINK ccache)
