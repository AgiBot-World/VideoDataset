#[[
Configure cppcheck for static analysisc when compiling a C++ project.

]]

include_guard(GLOBAL)

set(USE_CPPCHECK
    ON
    CACHE BOOL "Use cppcheck for static analysis of C++ code")

set(USE_CPPCHECK_OPTIONS
    --enable=style,performance,warning,portability
    --inline-suppr
    # We cannot act on a bug/missing feature of cppcheck
    --suppress=cppcheckError
    --suppress=internalAstError
    # if a file does not have an internalAstError, we get an
    # unmatchedSuppression error
    --suppress=unmatchedSuppression
    # noisy and incorrect sometimes
    --suppress=passedByValue
    # ignores code that cppcheck thinks is invalid C++
    --suppress=syntaxError
    --suppress=preprocessorErrorDirective
    --inconclusive
    CACHE STRING "cppcheck run options")

set(USE_CPPCHECK_SUPPRESSION_FILE
    ""
    CACHE FILEPATH "cppcheck suppression file")

set(USE_CPPCHECK_WARNINGS_AS_ERRORS
    OFF
    CACHE BOOL "Treat cppcheck warnings as errors")

message(
  STATUS
    "Use Cppcheck with USE_CPPCHECK: ${USE_CPPCHECK}
  Cppcheck Options:
    USE_CPPCHECK: If use cppcheck. Default is ON.
    USE_CPPCHECK_OPTIONS: cppcheck run options. Default is ${USE_CPPCHECK_OPTIONS}
    USE_CPPCHECK_SUPPRESSION_FILE: cppcheck suppression file pass to --suppressions-list option. Default is empty.
    USE_CPPCHECK_WARNINGS_AS_ERRORS: If treat warnings as errors. Default is OFF."
)

if(NOT USE_CPPCHECK)
  message(STATUS "Disable cppcheck by USE_CPPCHECK evaluates to false.")
  return()
endif()

find_program(
  CPPCHECK_COMMAND
  NAMES cppcheck
  DOC "Path to cppcheck executable")

if(NOT CPPCHECK_COMMAND)
  message(WARNING "No cppcheck found, disable cppcheck static analysis.")
  return()
endif()

set(CMAKE_CXX_CPPCHECK ${CPPCHECK_COMMAND} ${USE_CPPCHECK_OPTIONS})

# Set cppcheck template based on the generator used
if(CMAKE_GENERATOR MATCHES ".*Visual Studio.*")
  set(CPPCHECK_TEMPLATE "vs")
else()
  set(CPPCHECK_TEMPLATE "gcc")
endif()

# Prepend the template to the options
list(INSERT CMAKE_CXX_CPPCHECK 1 --template=${CPPCHECK_TEMPLATE})

# Add the standard to the cppcheck options
if(NOT "${CMAKE_CXX_STANDARD}" STREQUAL "")
  list(INSERT CMAKE_CXX_CPPCHECK 1 --std=c++${CMAKE_CXX_STANDARD})
endif()

# Suppress warnings in the build directory
list(APPEND CMAKE_CXX_CPPCHECK --suppress=*:${CMAKE_CURRENT_BINARY_DIR}/*)

# Add vcpkg include to the cppcheck search path and suppress it
if(VCPKG_INSTALLED_DIR AND VCPKG_TARGET_TRIPLET)
  list(APPEND CMAKE_CXX_CPPCHECK
       -I${VCPKG_INSTALLED_DIR}/${VCPKG_TARGET_TRIPLET}/include
       --suppress=*:${VCPKG_INSTALLED_DIR}/${VCPKG_TARGET_TRIPLET}/*)
endif()

# Add cppcheck suppression file
if(EXISTS "${USE_CPPCHECK_SUPPRESSION_FILE}")
  list(APPEND CMAKE_CXX_CPPCHECK
       --suppressions-list=${USE_CPPCHECK_SUPPRESSION_FILE})
endif()

if(USE_CPPCHECK_WARNINGS_AS_ERRORS)
  list(APPEND CMAKE_CXX_CPPCHECK --error-exitcode=2)
endif()

list(REMOVE_DUPLICATES CMAKE_CXX_CPPCHECK)
message(STATUS "Cppcheck final command: ${CMAKE_CXX_CPPCHECK}")
