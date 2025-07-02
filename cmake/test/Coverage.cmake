#[[
Copyright (c) 2022, 2023 msclock - msclock@qq.com

Copyright (C) 2018-2020 by George Cave - gcave@stablecoder.ca

Licensed under the Apache License, Version 2.0 (the "License"); you may not
use this file except in compliance with the License. You may obtain a copy of
the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations under
the License.
USAGE: To enable any code coverage instrumentation/targets, the single CMake
option of `CODE_COVERAGE` needs to be set to 'ON', either by GUI, ccmake, or
on the command line.

From this point, there are two primary methods for adding instrumentation to
targets: 1 - A blanket instrumentation by calling `add_code_coverage()`, where
all targets in that directory and all subdirectories are automatically
instrumented. 2 - Per-target instrumentation by calling
`target_code_coverage(<TARGET_NAME>)`, where the target is given and thus only
that target is instrumented. This applies to both libraries and executables.

To add coverage targets, such as calling `make ccov` to generate the actual
coverage information for perusal or consumption, call
`target_code_coverage(<TARGET_NAME>)` on an *executable* target.

Example 1: All targets instrumented

In this case, the coverage information reported will will be that of the
`theLib` library target and `theExe` executable.

1a: Via global command

 ~~~
 add_code_coverage() # Adds instrumentation to all targets

 add_library(theLib lib.cpp)

 add_executable(theExe main.cpp)
 target_link_libraries(theExe PRIVATE theLib)
 # As an executable target, adds the 'ccov-theExe' target (instrumentation already added via global nyways) for generating code coverage reports.
 target_code_coverage(theExe)
 ~~~

1b: Via target commands

 ~~~
 add_library(theLib lib.cpp)
 target_code_coverage(theLib) # As a library target, adds coverage instrumentation but no targets.

 add_executable(theExe main.cpp)
 target_link_libraries(theExe PRIVATE theLib)
 # As an executable target, adds the 'ccov-theExe' target and instrumentation for generating code overage reports.
 target_code_coverage(theExe)
 ~~~

Example 2: Target instrumented, but with regex pattern of files to be excluded
from report

 ~~~
 add_executable(theExe main.cpp non_covered.cpp)
 # As an executable target, the reports will exclude the non-covered.cpp file, and any files in a test/ folder.
 target_code_coverage(theExe EXCLUDE non_covered.cpp test/*)
 ~~~

Example 3: Target added to the 'ccov' and 'ccov-all' targets

 ~~~
 add_code_coverage_all_targets(EXCLUDE test/*) # Adds the 'ccov-all' target set and sets it to exclude all files in test/ folders.

 add_executable(theExe main.cpp non_covered.cpp)
 # As an executable target, adds to the 'ccov' and ccov-all' argets, and the reports will exclude the non-covered.cpp file, and any files in a test/ folder.
 target_code_coverage(theExe AUTO ALL EXCLUDE non_covered.cpp test/*)
 ~~~

Enable ctest *Coverage, such as ctest -T Experimental[Coverage] by msclock
]]

option(CODE_COVERAGE "Enables code coverage instrumentation and targets." ON)

set(CODE_COVERAGE_GCOVR_REPORT_FORMAT
    "lcov"
    CACHE STRING "Sets the gcovr report format.")

set(CODE_COVERAGE_GCOV
    "gcov"
    CACHE STRING "Sets the gcov executable to find in find_program().")

if(CMAKE_C_COMPILER_ID MATCHES [[(Apple)?Clang]] OR CMAKE_CXX_COMPILER_ID
                                                    MATCHES [[(Apple)?Clang]])
  set(CODE_COVERAGE_EXTRA_FLAGS
      "gcov -s ${CMAKE_BINARY_DIR}"
      CACHE STRING "Extra command line flags to pass to ctest *Coverage")
elseif(CMAKE_C_COMPILER_ID MATCHES "GNU" OR CMAKE_CXX_COMPILER_ID MATCHES "GNU")
  set(CODE_COVERAGE_EXTRA_FLAGS
      "-s ${CMAKE_BINARY_DIR}"
      CACHE STRING "Extra command line flags to pass to ctest *Coverage")
endif()

set(CODE_COVERAGE_LCOV_EXTRA_FLAGS
    "--ignore-errors=gcov,mismatch,mismatch"
    CACHE STRING "Extra command line flags to pass to lcov.")

set(CODE_COVERAGE_GCOVR_EXTRA_FLAGS
    "--gcov-ignore-errors=source_not_found"
    CACHE STRING "Extra command line flags to pass to lcov.")

message(
  STATUS
    "Use code coverage with CODE_COVERAGE: ${CODE_COVERAGE}
  Available Options:
    CODE_COVERAGE: ON/OFF - Enables/Disables code coverage. Default is ${CODE_COVERAGE}.
      ON - Enables code coverage with auto-selected supported tools.
          - llvm-cov: preferred for clang compilers.
          - lcov: preferred for gcc compilers.
          - opencppcoverage: preferred for msvc compilers.
          - gcovr: preferred for non-msvc compilers.
      OFF - Disables code coverage.
    CODE_COVERAGE_GCOV: Sets the gcov executable to find in find_program(). Default is ${CODE_COVERAGE_GCOV}.
    CODE_COVERAGE_GCOVR_REPORT_FORMAT: Sets the gcovr report format. Default is ${CODE_COVERAGE_GCOVR_REPORT_FORMAT}.
    CODE_COVERAGE_GCOVR_EXTRA_FLAGS: Extra command line flags to pass to gcovr. Default is ${CODE_COVERAGE_GCOVR_EXTRA_FLAGS}.
    CODE_COVERAGE_LCOV_EXTRA_FLAGS: Extra command line flags to pass to lcov. Default is ${CODE_COVERAGE_LCOV_EXTRA_FLAGS}.
    CODE_COVERAGE_EXTRA_FLAGS: Extra command line flags to pass to ctest *Coverage. Default is ${CODE_COVERAGE_EXTRA_FLAGS}."
)

if(NOT CODE_COVERAGE)
  message(STATUS "Code coverage disabled by CODE_COVERAGE evaluates to false.")
endif()

# Programs to generate coverage tools
find_program(LLVM_COV_PATH llvm-cov)
find_program(LLVM_PROFDATA_PATH llvm-profdata)
find_program(LCOV_PATH lcov)
find_program(GCOV_PATH ${CODE_COVERAGE_GCOV})
find_program(GENHTML_PATH genhtml)
find_program(GCOVR_PATH gcovr)
find_program(OCC_PATH NAMES OpenCppCoverage)

# Hide behind the 'advanced' mode flag for GUI/ccmake
mark_as_advanced(
  FORCE
  LLVM_COV_PATH
  LLVM_PROFDATA_PATH
  GCOV_PATH
  LCOV_PATH
  GENHTML_PATH
  GCOVR_PATH
  OCC_PATH)

# Variables
if(NOT CMAKE_COVERAGE_OUTPUT_DIRECTORY)
  set(CMAKE_COVERAGE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/code_coverage)
endif()

file(MAKE_DIRECTORY ${CMAKE_COVERAGE_OUTPUT_DIRECTORY})

set_property(GLOBAL PROPERTY JOB_POOLS ccov_serial_pool=1)

# Common initialization and checks
if(CODE_COVERAGE AND NOT CODE_COVERAGE_INITIALIZED)
  set(CODE_COVERAGE_INITIALIZED ON)

  # Enable ctest *Coverage, such as ctest -T
  # Continuous/Experimental/Nightly[Coverage]
  if(CMAKE_C_COMPILER_ID MATCHES [[(Apple)?Clang]] OR CMAKE_CXX_COMPILER_ID
                                                      MATCHES [[(Apple)?Clang]])
    set(COVERAGE_COMMAND
        "${LLVM_COV_PATH}"
        CACHE STRING "LLVM coverage tool for gcov" FORCE)
    if(LLVM_COV_PATH)
      set(COVERAGE_EXTRA_FLAGS
          "${CODE_COVERAGE_EXTRA_FLAGS}"
          CACHE STRING "Extra command line flags to pass to the coverage tool"
                FORCE)
    endif()
  elseif(CMAKE_C_COMPILER_ID MATCHES "GNU" OR CMAKE_CXX_COMPILER_ID MATCHES
                                              "GNU")
    if(GCOV_PATH)
      set(COVERAGE_EXTRA_FLAGS
          "${CODE_COVERAGE_EXTRA_FLAGS}"
          CACHE STRING "Extra command line flags to pass to the coverage tool"
                FORCE)
    endif(GCOV_PATH)
  endif()

  # Common Targets
  if(CMAKE_C_COMPILER_ID MATCHES [[(Apple)?Clang]] OR CMAKE_CXX_COMPILER_ID
                                                      MATCHES [[(Apple)?Clang]])
    if(CMAKE_C_COMPILER_ID MATCHES [[AppleClang]] OR CMAKE_CXX_COMPILER_ID
                                                     MATCHES [[AppleClang]])
      # When on macOS and using the Apple-provided toolchain, use the
      # XCode-provided llvm toolchain via `xcrun`
      message(
        STATUS
          "Building with XCode-provided llvm code coverage tools (via `xcrun`)")
      set(LLVM_COV_PATH xcrun llvm-cov)
      set(LLVM_PROFDATA_PATH xcrun llvm-profdata)
    endif()

    if(NOT LLVM_COV_PATH)
      message(FATAL_ERROR "llvm-cov not found! Aborting.")
    else()
      # Version number checking for 'EXCLUDE' compatibility
      execute_process(COMMAND ${LLVM_COV_PATH} --version
                      OUTPUT_VARIABLE LLVM_COV_VERSION_CALL_OUTPUT)

      string(REGEX MATCH "[0-9]+\\.[0-9]+\\.[0-9]+" LLVM_COV_VERSION
                   ${LLVM_COV_VERSION_CALL_OUTPUT})

      if(LLVM_COV_VERSION VERSION_LESS "7.0.0")
        message(
          WARNING
            "target_code_coverage()/add_code_coverage_all_targets() 'EXCLUDE' option only available on llvm-cov >= 7.0.0"
        )
      endif()
    endif()

    add_custom_target(
      ccov-clean
      COMMAND ${CMAKE_COMMAND} -E rm -f
              ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/binaries.list
      COMMAND ${CMAKE_COMMAND} -E rm -f
              ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/profraw.list)

    # Used to get the shared object file list before doing the main all-
    # processing
    add_custom_target(
      ccov-libs
      COMMAND ;
      COMMENT "libs ready for coverage report.")

  elseif(CMAKE_C_COMPILER_ID MATCHES "GNU" OR CMAKE_CXX_COMPILER_ID MATCHES
                                              "GNU")
    if(CMAKE_BUILD_TYPE)
      string(TOUPPER ${CMAKE_BUILD_TYPE} upper_build_type)

      if(NOT ${upper_build_type} STREQUAL "DEBUG")
        message(
          WARNING
            "Code coverage results with an optimized (non-Debug) build may be misleading"
        )
      endif()
    endif()

    if(NOT LLVM_COV_PATH
       AND NOT LCOV_PATH
       AND NOT GENHTML_PATH
       AND NOT GCOVR_PATH
       AND NOT OCC_PATH)
      message(
        FATAL_ERROR
          "At least one of llvm-cov, lcov, genhtml, opencppcoverage, or gcovr not found! Aborting..."
      )
    endif()

    # Targets
    if(LCOV_PATH)
      add_custom_target(ccov-clean COMMAND ${LCOV_PATH} --directory
                                           ${CMAKE_BINARY_DIR} --zerocounters)
      execute_process(
        COMMAND "${LCOV_PATH}" --version
        RESULT_VARIABLE _result
        OUTPUT_VARIABLE _output
        OUTPUT_STRIP_TRAILING_WHITESPACE)
      message(STATUS "_output: ${_output}")
      if(_result EQUAL 0 AND _output MATCHES " LCOV version ([0-9]+)")
        set(LCOV_MAJOR_VERSION "${CMAKE_MATCH_1}")
        if(LCOV_MAJOR_VERSION VERSION_LESS "2"
           AND CODE_COVERAGE_LCOV_EXTRA_FLAGS MATCHES "mismatch")
          message(
            WARNING
              "Does not support mismatch by lcov less 2 and remove params from ${CODE_COVERAGE_LCOV_EXTRA_FLAGS}..."
          )
          string(REPLACE [[mismatch]] "" CODE_COVERAGE_LCOV_EXTRA_FLAGS
                         ${CODE_COVERAGE_LCOV_EXTRA_FLAGS})
          set(CODE_COVERAGE_LCOV_EXTRA_FLAGS
              "${CODE_COVERAGE_LCOV_EXTRA_FLAGS}"
              CACHE STRING "Extra flags to pass to lcov" FORCE)
          message(
            STATUS
              "Final CODE_COVERAGE_LCOV_EXTRA_FLAGS: ${CODE_COVERAGE_LCOV_EXTRA_FLAGS}"
          )
        endif()
      endif()
    endif()

  elseif(CMAKE_C_COMPILER_ID MATCHES [[MSVC]] OR CMAKE_CXX_COMPILER_ID MATCHES
                                                 [[MSVC]])
    # Enable Visual Studio's CodeCoverage by static code coverage
    if(WIN32 AND MSVC)
      add_link_options(/PROFILE)
    endif()
  else()
    message(FATAL_ERROR "Code coverage requires Clang or GCC. Aborting.")
  endif()
endif()

# Adds code coverage instrumentation to a library, or instrumentation/targets
# for an executable target.
# ~~~
# EXECUTABLE ADDED TARGETS:
# GCOV/LCOV:
# ccov : Generates HTML code coverage report for every target added with 'AUTO' parameter.
# ccov-${TARGET_NAME} : Generates HTML code coverage report for the associated named target.
# ccov-all : Generates HTML code coverage report, merging every target added with 'ALL' parameter into a single detailed report.
#
# LLVM-COV:
# ccov : Generates HTML code coverage report for every target added with 'AUTO' parameter.
# ccov-report : Generates HTML code coverage report for every target added with 'AUTO' parameter.
# ccov-${TARGET_NAME} : Generates HTML code coverage report.
# ccov-report-${TARGET_NAME} : Prints to command line summary per-file coverage information.
# ccov-export-${TARGET_NAME} : Exports the coverage report to a JSON file.
# ccov-show-${TARGET_NAME} : Prints to command line detailed per-line coverage information.
# ccov-all : Generates HTML code coverage report, merging every target added with 'ALL' parameter into a single detailed report.
# ccov-all-report : Prints summary per-file coverage information for every target added with ALL' parameter to the command line.
# ccov-all-export : Exports the coverage report to a JSON file.
#
# Required:
# TARGET_NAME - Name of the target to generate code coverage for.
# Optional:
# PUBLIC - Sets the visibility for added compile options to targets to PUBLIC instead of the default of PRIVATE.
# INTERFACE - Sets the visibility for added compile options to targets to INTERFACE instead of the default of PRIVATE.
# PLAIN - Do not set any target visibility (backward compatibility with old cmake projects)
# AUTO - Adds the target to the 'ccov' target so that it can be run in a batch with others easily. Effective on executable targets.
# ALL - Adds the target to the 'ccov-all' and 'ccov-all-report' targets, which merge several executable targets coverage data to a single report. Effective on executable targets.
# EXTERNAL - For GCC's lcov, allows the profiling of 'external' files from the processing directory
# COVERAGE_TARGET_NAME - For executables ONLY, changes the outgoing target name so instead of `ccov-${TARGET_NAME}` it becomes `ccov-${COVERAGE_TARGET_NAME}`.
# EXCLUDE_DIRS <dirs> - Excludes the given directories from the coverage report. **These do not copy to the 'all' targets.**
# OBJECTS <TARGETS> - For executables ONLY, if the provided targets are shared libraries, adds coverage information to the output
# PRE_ARGS <ARGUMENTS> - For executables ONLY, prefixes given arguments to the associated ccov-* executable call ($<PRE_ARGS> ccov-*)
# ARGS <ARGUMENTS> - For executables ONLY, appends the given arguments to the associated ccov-* executable call (ccov-* $<ARGS>)
# ~~~
function(target_code_coverage TARGET_NAME)
  set(_opts AUTO ALL EXTERNAL PUBLIC INTERFACE PLAIN)
  set(_single_opts COVERAGE_TARGET_NAME)
  set(_multi_opts EXCLUDE OBJECTS PRE_ARGS ARGS)
  cmake_parse_arguments(PARSE_ARGV 0 "arg" "${_opts}" "${_single_opts}"
                        "${_multi_opts}")

  # Set the visibility of target functions to PUBLIC, INTERFACE or default to
  # PRIVATE.
  if(arg_PUBLIC)
    set(TARGET_VISIBILITY PUBLIC)
    set(TARGET_LINK_VISIBILITY PUBLIC)
  elseif(arg_INTERFACE)
    set(TARGET_VISIBILITY INTERFACE)
    set(TARGET_LINK_VISIBILITY INTERFACE)
  elseif(arg_PLAIN)
    set(TARGET_VISIBILITY PUBLIC)
    set(TARGET_LINK_VISIBILITY)
  else()
    set(TARGET_VISIBILITY PRIVATE)
    set(TARGET_LINK_VISIBILITY PRIVATE)
  endif()

  if(NOT arg_COVERAGE_TARGET_NAME)
    # If a specific name was given, use that instead.
    set(arg_COVERAGE_TARGET_NAME ${TARGET_NAME})
  endif()

  if(${arg_COVERAGE_TARGET_NAME} STREQUAL "coverage" OR ${TARGET_NAME} STREQUAL
                                                        "coverage")
    message(
      FATAL_ERROR
        "Target name 'coverage' is reserved for the 'add_code_coverage_all_targets' function. Please choose a different name."
    )
  endif()

  if(CODE_COVERAGE)
    # Add code coverage instrumentation to the target's linker command
    if(CMAKE_C_COMPILER_ID MATCHES [[(Apple)?Clang]]
       OR CMAKE_CXX_COMPILER_ID MATCHES [[(Apple)?Clang]])
      target_compile_options(
        ${TARGET_NAME} ${TARGET_VISIBILITY} -fprofile-instr-generate
        -fcoverage-mapping --coverage)
      target_link_options(${TARGET_NAME} ${TARGET_VISIBILITY}
                          -fprofile-instr-generate -fcoverage-mapping)
    elseif(CMAKE_C_COMPILER_ID MATCHES "GNU" OR CMAKE_CXX_COMPILER_ID MATCHES
                                                "GNU")
      target_compile_options(
        ${TARGET_NAME} ${TARGET_VISIBILITY} --coverage
        $<$<COMPILE_LANGUAGE:CXX>:-fno-elide-constructors> -fno-default-inline)
      target_link_libraries(${TARGET_NAME} ${TARGET_LINK_VISIBILITY} gcov)
    endif()

    # Targets
    get_target_property(_target_type ${TARGET_NAME} TYPE)

    # Add shared library to processing for 'all' targets
    if(_target_type STREQUAL "SHARED_LIBRARY" AND arg_ALL)
      if(CMAKE_C_COMPILER_ID MATCHES [[(Apple)?Clang]]
         OR CMAKE_CXX_COMPILER_ID MATCHES [[(Apple)?Clang]])
        add_custom_target(
          ccov-run-${arg_COVERAGE_TARGET_NAME}
          COMMAND
            ${CMAKE_COMMAND} -E echo "-object=$<TARGET_FILE:${TARGET_NAME}>" >>
            ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/binaries.list
          DEPENDS ${TARGET_NAME})

        if(NOT TARGET ccov-libs)
          message(
            FATAL_ERROR
              "Calling target_code_coverage with 'ALL' must be after a call to 'add_code_coverage_all_targets'."
          )
        endif()

        add_dependencies(ccov-libs ccov-run-${arg_COVERAGE_TARGET_NAME})
      endif()

      if(MSVC)
        add_dependencies(ccov-all-processing ${TARGET_NAME})
      endif()
    endif()

    # For executables add targets to run and produce output
    if(_target_type STREQUAL "EXECUTABLE")
      if(CMAKE_C_COMPILER_ID MATCHES [[(Apple)?Clang]]
         OR CMAKE_CXX_COMPILER_ID MATCHES [[(Apple)?Clang]])
        # If there are shared objects to also work with, generate the string to
        # add them here
        foreach(_so_target ${arg_OBJECTS})
          # Check to see if the target is a shared object
          if(TARGET ${_so_target})
            get_target_property(_so_target_type ${_so_target} TYPE)

            if(${_so_target_type} STREQUAL "SHARED_LIBRARY")
              set(_so_objects ${_so_objects}
                              -object=$<TARGET_FILE:${_so_target}>)
            endif()
          endif()
        endforeach()

        # Run the executable, generating raw profile data Make the run data
        # available for further processing. Separated to allow Windows to run
        # this target serially.
        add_custom_target(
          ccov-run-${arg_COVERAGE_TARGET_NAME}
          COMMAND
            ${CMAKE_COMMAND} -E env
            LLVM_PROFILE_FILE=${arg_COVERAGE_TARGET_NAME}.profraw
            $<TARGET_FILE:${TARGET_NAME}> ${arg_ARGS}
          COMMAND
            ${CMAKE_COMMAND} -E echo "-object=$<TARGET_FILE:${TARGET_NAME}>"
            ${_so_objects} >> ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/binaries.list
          COMMAND
            ${CMAKE_COMMAND} -E echo
            "${CMAKE_CURRENT_BINARY_DIR}/${arg_COVERAGE_TARGET_NAME}.profraw" >>
            ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/profraw.list
          JOB_POOL ccov_serial_pool
          DEPENDS ccov-libs ${TARGET_NAME})

        # Merge the generated profile data so llvm-cov can process it
        add_custom_target(
          ccov-processing-${arg_COVERAGE_TARGET_NAME}
          COMMAND
            ${LLVM_PROFDATA_PATH} merge -sparse
            ${arg_COVERAGE_TARGET_NAME}.profraw -o
            ${arg_COVERAGE_TARGET_NAME}.profdata
          DEPENDS ccov-run-${arg_COVERAGE_TARGET_NAME})

        # Ignore regex only works on LLVM >= 7
        if(LLVM_COV_VERSION VERSION_GREATER_EQUAL "7.0.0")
          foreach(_dir ${arg_EXCLUDE_DIRS})
            set(_exclude_regex ${_exclude_regex}
                               -ignore-filename-regex='${_dir}/*')
          endforeach()
        endif()

        # Print out details of the coverage information to the command line
        add_custom_target(
          ccov-show-${arg_COVERAGE_TARGET_NAME}
          COMMAND
            ${LLVM_COV_PATH} show $<TARGET_FILE:${TARGET_NAME}> ${_so_objects}
            -instr-profile=${arg_COVERAGE_TARGET_NAME}.profdata
            -show-line-counts-or-regions ${_exclude_regex}
          DEPENDS ccov-processing-${arg_COVERAGE_TARGET_NAME})

        # Print out a summary of the coverage information to the command line
        add_custom_target(
          ccov-report-${arg_COVERAGE_TARGET_NAME}
          COMMAND
            ${LLVM_COV_PATH} report $<TARGET_FILE:${TARGET_NAME}> ${_so_objects}
            -instr-profile=${arg_COVERAGE_TARGET_NAME}.profdata
            ${_exclude_regex}
          DEPENDS ccov-processing-${arg_COVERAGE_TARGET_NAME})

        # Export coverage information so continuous integration tools (e.g.
        # Jenkins) can consume it
        add_custom_target(
          ccov-export-${arg_COVERAGE_TARGET_NAME}
          COMMAND
            ${LLVM_COV_PATH} export $<TARGET_FILE:${TARGET_NAME}> ${_so_objects}
            -instr-profile=${arg_COVERAGE_TARGET_NAME}.profdata -format="lcov"
            ${_exclude_regex} >
            ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/${arg_COVERAGE_TARGET_NAME}.info
          DEPENDS ccov-processing-${arg_COVERAGE_TARGET_NAME})

        # Generates HTML output of the coverage information for perusal
        add_custom_target(
          ccov-${arg_COVERAGE_TARGET_NAME}
          COMMAND
            ${LLVM_COV_PATH} show $<TARGET_FILE:${TARGET_NAME}> ${_so_objects}
            -instr-profile=${arg_COVERAGE_TARGET_NAME}.profdata
            -show-line-counts-or-regions
            -output-dir=${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/${arg_COVERAGE_TARGET_NAME}
            -format="html" ${_exclude_regex}
          DEPENDS ccov-processing-${arg_COVERAGE_TARGET_NAME})

      elseif(CMAKE_C_COMPILER_ID MATCHES "GNU" OR CMAKE_CXX_COMPILER_ID MATCHES
                                                  "GNU")
        set(_coverage_info
            "${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/${arg_COVERAGE_TARGET_NAME}.info"
        )

        # Run the executable, generating coverage information
        add_custom_target(
          ccov-run-${arg_COVERAGE_TARGET_NAME}
          COMMAND ${CMAKE_CROSSCOMPILING_EMULATOR} ${arg_PRE_ARGS}
                  $<TARGET_FILE:${TARGET_NAME}> ${arg_ARGS}
          DEPENDS ${TARGET_NAME})

        # GCC/lcov excludes by glob pattern Exclusion glob pattern string
        # creation
        set(_exclude_glob)

        # Generate exclusion string for use
        foreach(_dir ${arg_EXCLUDE_DIRS})
          set(_exclude_glob ${_exclude_glob} --remove ${_coverage_info}
                            '${_dir}/*')
        endforeach()

        if(_exclude_glob)
          set(_exclude_glob_command ${LCOV_PATH} ${_exclude_glob} --output-file
                                    ${_coverage_info})
        else()
          set(_exclude_glob_command ;)
        endif()

        if(NOT ${arg_EXTERNAL})
          set(EXTERNAL_OPTION --no-external)
        endif()

        set(GCOV_OPTION)

        if(GCOV_PATH)
          set(GCOV_OPTION --gcov-tool "${GCOV_PATH}")
        endif()

        # Capture the coverage information
        add_custom_target(
          ccov-capture-${arg_COVERAGE_TARGET_NAME}
          COMMAND ${CMAKE_COMMAND} -E rm -f ${_coverage_info}
          COMMAND ${LCOV_PATH} --directory ${CMAKE_BINARY_DIR} --zerocounters
          COMMAND ${CMAKE_CROSSCOMPILING_EMULATOR} ${arg_PRE_ARGS}
                  $<TARGET_FILE:${TARGET_NAME}> ${arg_ARGS}
          COMMAND
            ${LCOV_PATH} --directory ${CMAKE_BINARY_DIR} --base-directory
            ${CMAKE_SOURCE_DIR} --capture --output-file ${EXTERNAL_OPTION}
            ${_coverage_info} ${GCOV_OPTION} ${CODE_COVERAGE_LCOV_EXTRA_FLAGS}
          COMMAND ${_exclude_glob_command}
          DEPENDS ${TARGET_NAME})

        # Generates HTML output of the coverage information for perusal
        add_custom_target(
          ccov-${arg_COVERAGE_TARGET_NAME}
          COMMAND
            ${GENHTML_PATH} -o
            ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/${arg_COVERAGE_TARGET_NAME}
            ${_coverage_info}
          DEPENDS ccov-capture-${arg_COVERAGE_TARGET_NAME})
      endif()

      if(NOT MSVC)
        add_custom_command(
          TARGET ccov-${arg_COVERAGE_TARGET_NAME}
          POST_BUILD
          COMMAND ;
          COMMENT
            "Open ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/${arg_COVERAGE_TARGET_NAME}/index.html in your browser to view the coverage report."
        )

        # AUTO
        if(arg_AUTO)
          if(NOT TARGET ccov)
            add_custom_target(ccov)
          endif()

          add_dependencies(ccov ccov-${arg_COVERAGE_TARGET_NAME})

          if(NOT CMAKE_C_COMPILER_ID MATCHES "GNU"
             AND NOT CMAKE_CXX_COMPILER_ID MATCHES "GNU")
            if(NOT TARGET ccov-report)
              add_custom_target(ccov-report)
            endif()

            add_dependencies(ccov-report
                             ccov-report-${arg_COVERAGE_TARGET_NAME})
          endif()
        endif()
      endif(NOT MSVC)

      # ALL
      if(arg_ALL)
        if(NOT TARGET ccov-all-processing)
          message(
            FATAL_ERROR
              "Calling target_code_coverage with 'ALL' must be after a call to 'add_code_coverage_all_targets'."
          )
        endif()

        if(NOT MSVC)
          add_dependencies(ccov-all-processing
                           ccov-run-${arg_COVERAGE_TARGET_NAME})
        else()
          add_dependencies(ccov-all-processing ${TARGET_NAME})
        endif()
      endif()
    endif()
  endif()
endfunction()

# Adds code coverage instrumentation to all targets in the current directory and
# any subdirectories. To add coverage instrumentation to only specific targets,
# use `target_code_coverage`.
function(add_code_coverage)
  if(CODE_COVERAGE)
    if(CMAKE_C_COMPILER_ID MATCHES [[(Apple)?Clang]]
       OR CMAKE_CXX_COMPILER_ID MATCHES [[(Apple)?Clang]])
      add_compile_options(-fprofile-instr-generate -fcoverage-mapping)
      add_link_options(-fprofile-instr-generate -fcoverage-mapping)
    elseif(CMAKE_C_COMPILER_ID MATCHES "GNU" OR CMAKE_CXX_COMPILER_ID MATCHES
                                                "GNU")
      add_compile_options(
        -fprofile-arcs -ftest-coverage
        $<$<COMPILE_LANGUAGE:CXX>:-fno-elide-constructors> -fno-default-inline)
      link_libraries(gcov)
    endif()
  endif()
endfunction()

# Adds the 'ccov-all' type targets that calls all targets added via
# `target_code_coverage` with the `ALL` parameter, but merges all the coverage
# data from them into a single large report  instead of the numerous smaller
# reports. Also adds the ccov-all-capture Generates an all-merged.info file, for
# use with coverage dashboards (e.g. codecov.io, coveralls).
# ~~~
# Optional:
# EXCLUDE_DIRS <DIRS> - Excludes directories including source files from evaluation of coverage.
# INCLUDE_DIRS <DIRS> - Include directories including source files to evaluate coverage.
# ~~~
function(add_code_coverage_all_targets)
  set(_single_opts)
  set(_multi_opts EXCLUDE_DIRS INCLUDE_DIRS)
  cmake_parse_arguments(PARSE_ARGV 0 "arg" "" "${_single_opts}"
                        "${_multi_opts}")

  if(CODE_COVERAGE)
    if(NOT arg_INCLUDE_DIRS)
      message(
        FATAL_ERROR
          "Calling add_code_coverage_all_targets with OCC requires the INCLUDE_DIRS option to be set."
      )
    endif()

    if(OCC_PATH AND MSVC)
      message(STATUS "Using preferred OpenCppCoverage for msvc")
      # Nothing required for occ
      add_custom_target(ccov-all-processing COMMAND ;)

      foreach(_dir ${arg_INCLUDE_DIRS})
        cmake_path(CONVERT ${_dir} TO_NATIVE_PATH_LIST _dir)
        list(APPEND _include_command "--sources")
        list(APPEND _include_command "${_dir}")
      endforeach()

      foreach(_dir ${arg_EXCLUDE_DIRS})
        cmake_path(CONVERT ${_dir} TO_NATIVE_PATH_LIST _dir)
        list(APPEND _exclude_command "--excluded_sources")
        list(APPEND _exclude_command "${_dir}")
      endforeach()

      # Generate the coverage report using OpenCppCoverage
      add_custom_target(
        ccov-all-capture
        COMMAND ${CMAKE_COMMAND} -E rm -f
                ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/coverage.xml
        COMMAND
          ${OCC_PATH} --export_type
          cobertura:${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/coverage.xml
          --working_dir ${CMAKE_SOURCE_DIR} ${_include_command}
          ${_exclude_command} --cover_children -- ${CMAKE_COMMAND} --build
          ${CMAKE_BINARY_DIR} --target ExperimentalTest;
        DEPENDS ccov-all-processing)

      # Generates HTML output of all targets for perusal
      add_custom_target(
        ccov-all
        COMMAND ${CMAKE_COMMAND} -E rm -rf
                ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/coverage
        COMMAND
          ${OCC_PATH} --export_type
          html:${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/coverage --working_dir
          ${CMAKE_SOURCE_DIR} ${_include_command} ${_exclude_command}
          --cover_children -- ${CMAKE_COMMAND} --build ${CMAKE_BINARY_DIR}
          --target ExperimentalTest;
        DEPENDS ccov-all-capture)

      return()
    endif()

    if(GCOVR_PATH AND NOT MSVC)
      message(STATUS "Using preferred gcovr for non-msvc compilers")
      # Nothing required for gcovr
      add_custom_target(ccov-all-processing COMMAND ;)

      set(GCOV_OPTION)

      if(GCOV_PATH)
        if(CMAKE_C_COMPILER_ID MATCHES [[(Apple)?Clang]]
           OR CMAKE_CXX_COMPILER_ID MATCHES [[(Apple)?Clang]])
          set(GCOV_OPTION "--gcov-executable=${LLVM_COV_PATH} gcov")
        elseif(CMAKE_C_COMPILER_ID MATCHES "GNU" OR CMAKE_CXX_COMPILER_ID
                                                    MATCHES "GNU")
          set(GCOV_OPTION "--gcov-executable=${GCOV_PATH}")
        endif()
      endif()

      foreach(_dir ${arg_INCLUDE_DIRS})
        cmake_path(CONVERT ${_dir} TO_CMAKE_PATH_LIST _dir)
        list(APPEND _include_command "--filter")
        list(APPEND _include_command "${_dir}")
      endforeach()

      foreach(_dir ${arg_EXCLUDE_DIRS})
        cmake_path(CONVERT ${_dir} TO_CMAKE_PATH_LIST _dir)
        # gcovr prefers excludes by relative path
        file(RELATIVE_PATH _rel ${CMAKE_SOURCE_DIR} ${_dir})
        list(APPEND _exclude_command "--exclude")
        list(APPEND _exclude_command "${_rel}")
      endforeach()

      if(CODE_COVERAGE_GCOVR_REPORT_FORMAT MATCHES "lcov")
        set(_gcovr_format_option "--lcov")
        set(_gcovr_output_file "coverage.info")
      else()
        set(_gcovr_format_option "--xml-pretty")
        set(_gcovr_output_file "coverage.xml")
      endif()

      # Generate the coverage report using gcovr
      add_custom_target(
        ccov-all-capture
        COMMAND ${CMAKE_COMMAND} -E rm -f
                ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/${_gcovr_output_file}
        COMMAND
          ${GCOVR_PATH} --print-summary ${_gcovr_format_option} --root
          ${CMAKE_SOURCE_DIR} --output
          ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/${_gcovr_output_file}
          ${GCOV_OPTION} ${_include_command} ${_exclude_command}
          ${CODE_COVERAGE_GCOVR_EXTRA_FLAGS}
        DEPENDS ccov-all-processing)

      # Generates HTML output of all targets for perusal
      add_custom_target(
        ccov-all
        COMMAND ${CMAKE_COMMAND} -E rm -rf
                ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/coverage
        COMMAND ${CMAKE_COMMAND} -E make_directory
                ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/coverage
        COMMAND
          ${GCOVR_PATH} --html-details --root ${CMAKE_SOURCE_DIR} --output
          ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/coverage/index.html ${GCOV_OPTION}
          ${_include_command} ${_exclude_command}
          ${CODE_COVERAGE_GCOVR_EXTRA_FLAGS}
        DEPENDS ccov-all-capture)

      return()
    endif()

    if(CMAKE_C_COMPILER_ID MATCHES [[(Apple)?Clang]]
       OR CMAKE_CXX_COMPILER_ID MATCHES [[(Apple)?Clang]])
      # Merge the profile data for all of the run executables
      if(WIN32)
        add_custom_target(
          ccov-all-processing
          COMMAND
            powershell -Command $$FILELIST = Get-Content
            ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/profraw.list\; llvm-profdata.exe
            merge -o ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/all-merged.profdata
            -sparse $$FILELIST)
      else()
        add_custom_target(
          ccov-all-processing
          COMMAND
            ${LLVM_PROFDATA_PATH} merge -o
            ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/all-merged.profdata -sparse `cat
            ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/profraw.list`)
      endif()

      # Note that clang/LLVM excludes via regex! Regex exclude only available
      # for LLVM >= 7
      if(LLVM_COV_VERSION VERSION_GREATER_EQUAL "7.0.0")
        foreach(_dir ${arg_EXCLUDE_DIRS})
          set(_exclude_regex ${_exclude_regex}
                             -ignore-filename-regex='${_dir}/*')
        endforeach()
      endif()

      # Print summary of the code coverage information to the command line
      if(WIN32)
        add_custom_target(
          ccov-all-report
          COMMAND
            powershell -Command $$FILELIST = Get-Content
            ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/binaries.list\; llvm-cov.exe
            report $$FILELIST
            -instr-profile=${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/all-merged.profdata
            ${_exclude_regex}
          DEPENDS ccov-all-processing)
      else()
        add_custom_target(
          ccov-all-report
          COMMAND
            ${LLVM_COV_PATH} report `cat
            ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/binaries.list`
            -instr-profile=${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/all-merged.profdata
            ${_exclude_regex}
          DEPENDS ccov-all-processing)
      endif()

      # Export coverage information so continuous integration tools (e.g.
      # Jenkins or codecov.io) can consume it
      if(WIN32)
        add_custom_target(
          ccov-all-export
          COMMAND
            powershell -Command $$FILELIST = Get-Content
            ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/binaries.list\; llvm-cov.exe
            export $$FILELIST
            -instr-profile=${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/all-merged.profdata
            -format="lcov" ${_exclude_regex} >
            ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/coverage.info
          DEPENDS ccov-all-report)
      else()
        add_custom_target(
          ccov-all-export
          COMMAND
            ${LLVM_COV_PATH} export `cat
            ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/binaries.list`
            -instr-profile=${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/all-merged.profdata
            -format="lcov" ${_exclude_regex} >
            ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/coverage.info
          DEPENDS ccov-all-report)
      endif()

      # Generate HTML output of all added targets for perusal
      if(WIN32)
        add_custom_target(
          ccov-all
          COMMAND
            powershell -Command $$FILELIST = Get-Content
            ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/binaries.list\; llvm-cov.exe show
            $$FILELIST
            -instr-profile=${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/all-merged.profdata
            -show-line-counts-or-regions
            -output-dir=${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/coverage
            -format="html" ${_exclude_regex}
          DEPENDS ccov-all-export)
      else()
        add_custom_target(
          ccov-all
          COMMAND
            ${LLVM_COV_PATH} show `cat
            ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/binaries.list`
            -instr-profile=${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/all-merged.profdata
            -show-line-counts-or-regions
            -output-dir=${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/coverage
            -format="html" ${_exclude_regex}
          DEPENDS ccov-all-export)
      endif()

    elseif(CMAKE_C_COMPILER_ID MATCHES "GNU" OR CMAKE_CXX_COMPILER_ID MATCHES
                                                "GNU")
      set(_coverage_info "${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/coverage.info")

      # Nothing required for gcov
      add_custom_target(ccov-all-processing COMMAND ;)

      # GCC/lcov excludes by glob pattern Exclusion glob pattern string creation
      set(_exclude_glob)

      foreach(_dir ${arg_EXCLUDE_DIRS})
        set(_exclude_glob ${_exclude_glob} --remove ${_coverage_info}
                          '${_dir}/*')
      endforeach()

      if(_exclude_glob)
        set(_exclude_glob_command ${LCOV_PATH} ${_exclude_glob} --output-file
                                  ${_coverage_info})
      else()
        set(_exclude_glob_command ;)
      endif()

      set(GCOV_OPTION)

      if(GCOV_PATH)
        set(GCOV_OPTION --gcov-tool "${GCOV_PATH}")
      endif()

      # Capture coverage data
      add_custom_target(
        ccov-all-capture
        COMMAND ${CMAKE_COMMAND} -E rm -f ${_coverage_info}
        COMMAND
          ${LCOV_PATH} --directory ${CMAKE_BINARY_DIR} --capture --output-file
          ${_coverage_info} ${GCOV_OPTION} ${CODE_COVERAGE_LCOV_EXTRA_FLAGS}
        COMMAND ${_exclude_glob_command}
        DEPENDS ccov-all-processing)

      # Generates HTML output of all targets for perusal
      add_custom_target(
        ccov-all
        COMMAND
          ${GENHTML_PATH} --output-directory
          ${CMAKE_COVERAGE_OUTPUT_DIRECTORY}/coverage ${_coverage_info} --prefix
          ${CMAKE_SOURCE_DIR}
        DEPENDS ccov-all-capture)
    endif()
  endif()
endfunction()
