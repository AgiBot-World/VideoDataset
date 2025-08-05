#[[
This module contains default modules and settings that can be used by all projects.
]]

include_guard(GLOBAL)

# Prevent the module from being used in the wrong location
if(NOT CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
  message(FATAL_ERROR "This module should be in the project root directory")
endif()

include(${CMAKE_CURRENT_LIST_DIR}/configure/Default.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/build/Default.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/test/Default.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/install/Default.cmake)

function(sync_conan_hooks)
  # Install Conan hooks to the user home directory
  set(HOME_DIR "")
  if(WIN32)
    get_filename_component(HOME_DIR "$ENV{HOMEDRIVE}$ENV{HOMEPATH}" ABSOLUTE)
  else()
    get_filename_component(HOME_DIR "$ENV{HOME}" ABSOLUTE)
  endif()

  execute_process(
    COMMAND ${CMAKE_COMMAND} -E make_directory
            ${HOME_DIR}/.conan2/extensions/hooks
    COMMAND
      ${CMAKE_COMMAND} -E copy_if_different
      ${CMAKE_CURRENT_LIST_DIR}/hooks/hook_rewrite_url.py
      "${HOME_DIR}/.conan2/extensions/hooks/hook_rewrite_url.py"
    RESULT_VARIABLE
      return_code ECHO_ERROR_VARIABLE # show the text output regardless
      ECHO_OUTPUT_VARIABLE
    OUTPUT_STRIP_TRAILING_WHITESPACE
    WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR})

  if(NOT "${return_code}" STREQUAL "0")
    message(
      WARNING
        "CMake-Conan: Failed to install Conan hooks. Please copy it manually to ${HOME_DIR}/.conan2/extensions/hooks/."
    )
  endif()
endfunction()

sync_conan_hooks()

add_debug_macro()

create_uninstall_target()

# Include optional ProjectOptions.cmake for customizing project settings
if(EXISTS ${CMAKE_SOURCE_DIR}/cmake/ProjectOptions.cmake)
  include(${CMAKE_SOURCE_DIR}/cmake/ProjectOptions.cmake)
elseif(EXISTS ${CMAKE_SOURCE_DIR}/ProjectOptions.cmake)
  include(${CMAKE_SOURCE_DIR}/ProjectOptions.cmake)
endif()

# Add custom module path from the project
if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/CMake)
  list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/CMake")
elseif(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/cmake)
  list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
endif()

# Include general build and test settings for all projects
include(${CMAKE_CURRENT_LIST_DIR}/build/Sanitizer.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/test/Valgrind.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/build/ClangTidy.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/build/Cppcheck.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/build/CompilerFlags.cmake)
include(${CMAKE_CURRENT_LIST_DIR}/build/Hardening.cmake)

# Show information about the current project
cmake_language(DEFER DIRECTORY ${CMAKE_SOURCE_DIR} CALL show_project_version)
cmake_language(DEFER DIRECTORY ${CMAKE_SOURCE_DIR} CALL
               show_vcpkg_configuration)
cmake_language(DEFER DIRECTORY ${CMAKE_SOURCE_DIR} CALL show_installation)

# Cpack
set(__cpack_cmake_module
    ${CMAKE_CURRENT_LIST_DIR}/install/Cpack.cmake
    CACHE
      INTERNAL
      "Cpack module path to be included when directory CMAKE_SOURCE_DIR ends"
      FORCE)
cmake_language(DEFER DIRECTORY ${CMAKE_SOURCE_DIR} CALL include
               ${__cpack_cmake_module})
