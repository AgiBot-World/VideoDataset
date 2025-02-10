#[[
This module provides some common tools.
]]

include_guard(GLOBAL)

#[[
Show installation directories
]]
macro(show_installation)
  message(STATUS "Installation Paths:")
  foreach(_p LIB BIN INCLUDE CMAKE)
    file(TO_NATIVE_PATH ${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_${_p}DIR} _path)
    message(STATUS "\t${_p} installation path: ${_path}")
    unset(_path)
  endforeach()
endmacro()

#[[
A function to provide a target to uninstall things from the command `cmake install`.

It will create a file ``cmake_uninstall.cmake`` in the build directory and add a
custom target ``uninstall`` (or ``UNINSTALL`` on Visual Studio and Xcode) that
will remove the files installed by your package (using ``install_manifest.txt``).
See also https://gitlab.kitware.com/cmake/community/wikis/FAQ#can-i-do-make-uninstall-with-cmake

]]
function(create_uninstall_target)
  if(NOT "${CMAKE_CURRENT_BINARY_DIR}" STREQUAL "${CMAKE_BINARY_DIR}")
    message(FATAL_ERROR "Works only when included in the main CMakeLists.txt")
    return()
  endif()

  # The name of the target is uppercase in MSVC and Xcode (for coherence with
  # the other standard targets)
  if("${CMAKE_GENERATOR}" MATCHES "^(Visual Studio|Xcode)")
    set(_uninstall "UNINSTALL")
  else()
    set(_uninstall "uninstall")
  endif()

  # If target is already defined don't do anything
  if(TARGET ${_uninstall})
    return()
  endif()

  set(_cache_dir ${CMAKE_BINARY_DIR}/${CMAKE_CURRENT_FUNCTION})

  set(uninstall_script_config
      "
if(NOT EXISTS \"@CMAKE_BINARY_DIR@/install_manifest.txt\")
  message(FATAL_ERROR \"Cannot find install manifest: @CMAKE_BINARY_DIR@/install_manifest.txt\")
endif()

file(READ \"@CMAKE_BINARY_DIR@/install_manifest.txt\" files)
string(REGEX REPLACE \"\\n\" \"\;\" files \"\${files}\")
foreach(file \${files})
  message(STATUS \"Uninstalling \$ENV{DESTDIR}\${file}\")
  if(IS_SYMLINK \"\$ENV{DESTDIR}\${file}\" OR EXISTS \"\$ENV{DESTDIR}\${file}\")
    execute_process(
      COMMAND \${CMAKE_COMMAND} -E remove \"\$ENV{DESTDIR}\${file}\"
      OUTPUT_VARIABLE rm_out
      RESULT_VARIABLE rm_retval
    )
    if(NOT \"\${rm_retval}\" STREQUAL 0)
      message(FATAL_ERROR \"Problem when removing \$ENV{DESTDIR}\${file}\")
    endif()
  else(IS_SYMLINK \"\$ENV{DESTDIR}\${file}\" OR EXISTS \"\$ENV{DESTDIR}\${file}\")
    message(STATUS \"File \$ENV{DESTDIR}\${file} does not exist.\")
  endif()
endforeach()

function(get_empty_dir check_dir result_dirs)
  file(GLOB_RECURSE check_dirs LIST_DIRECTORIES true \"\${check_dir}/*\")
  list(REVERSE check_dirs)
  list(APPEND check_dirs \${check_dir})

  foreach(item \${check_dirs})
    if(IS_DIRECTORY \${item})
      file(GLOB_RECURSE dir_item_subdirs \"\${item}/*\")

      if(NOT dir_item_subdirs)
        list(APPEND _empty \${item})
      endif()
    endif()
  endforeach()

  set(\${result_dirs} \${_empty} PARENT_SCOPE)
endfunction()

get_empty_dir(\"@CMAKE_INSTALL_PREFIX@\" result_dirs)

foreach(empty_dir \${result_dirs})
  file(REMOVE_RECURSE \${empty_dir})
endforeach()
")

  set(_uninstall_file "${_cache_dir}/cmake_uninstall.cmake")
  file(WRITE "${_uninstall_file}.in" ${uninstall_script_config})

  set(_comment COMMENT "Uninstall the project...")

  # uninstall target
  if(NOT TARGET ${_uninstall})
    configure_file("${_uninstall_file}.in" "${_uninstall_file}" IMMEDIATE @ONLY)

    add_custom_target(
      ${_uninstall}
      ${_comment}
      COMMAND ${CMAKE_COMMAND} -P ${_uninstall_file}
      BYPRODUCTS uninstall_byproduct)
    set_property(SOURCE uninstall_byproduct PROPERTY SYMBOLIC 1)

    set_property(TARGET ${_uninstall} PROPERTY FOLDER "CMakePredefinedTargets")
  endif()

endfunction()
