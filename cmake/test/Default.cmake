#[[
Default to test
]]

include_guard(GLOBAL)

# This variable is only used when ``CMAKE_CROSSCOMPILING`` is on. It should
# point to a command on the host system that can run executable built for the
# target system.
if(WIN32 AND NOT ${CMAKE_HOST_SYSTEM_NAME} STREQUAL "Windows")
  # We're building for Windows on a different operating system.
  find_program(
    WINE
    NAMES "wine" "wine64" "wine-development"
    DOC "Wine (to run tests)")

  if(WINE)
    message(
      STATUS "The following Wine binary will be used to run tests: \"${WINE}\"")
    set(CMAKE_CROSSCOMPILING_EMULATOR ${WINE})
  else()
    message(
      WARNING
        "You are cross-compiling for Windows but don't have Wine, you will not be able to run tests."
    )
  endif()
endif()

include(${CMAKE_CURRENT_LIST_DIR}/Test.cmake)
