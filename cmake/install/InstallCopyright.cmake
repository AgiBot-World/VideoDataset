#[[
This module provides tools to handle cmake copyright installations painlessly.
]]

include_guard(GLOBAL)

#[[.md
A function to install copyrights.

Arguments:
  DESTINATION - destination path.(required)
  FILE_LIST - Specifies a list of license files with absolute paths. (required)
  COMMENT - adds a comment before at the top of the file.(optional)

Note:

  This function creates a file called copyright inside path DESTINATION.

  If more than one file is provided, this function concatenates the contents of multiple copyright files to a single file.

  The resulting copyright file looks similar to this:

    ```txt
    LICENSE-LGPL2.txt:

    Lorem ipsum dolor...

    LICENSE-MIT.txt:

    Lorem ipsum dolor sit amet...
    ```

  Or with COMMENT:

    ```txt
    A meaningful comment

    LICENSE-LGPL2.txt:

    Lorem ipsum dolor...

    LICENSE-MIT.txt:

    Lorem ipsum dolor sit amet...
    ```

Example:
  install_copyright(FILE_LIST "${SOURCE_PATH}/LICENSE/license.md" "${SOURCE_PATH}/LICENSE/license_gpl.md" COMMENT "This is a comment")

  file(GLOB LICENSE_FILES "${SOURCE_PATH}/LICENSES/*")
  install_copyright(FILE_LIST ${LICENSE_FILES} DESTINATION share/somewhere)

]]
function(install_copyright)
  cmake_parse_arguments(PARSE_ARGV 0 arg "" "COMMENT;DESTINATION" "FILE_LIST")

  if(DEFINED arg_UNPARSED_ARGUMENTS)
    message(
      FATAL_ERROR
        "${CMAKE_CURRENT_FUNCTION} was passed extra arguments: ${arg_UNPARSED_ARGUMENTS}"
    )
  endif()

  if(NOT DEFINED arg_FILE_LIST)
    message(FATAL_ERROR "FILE_LIST must be specified")
  endif()

  if(NOT DEFINED arg_DESTINATION)
    message(FATAL_ERROR "DESTINATION must be specified and exist")
  endif()

  list(LENGTH arg_FILE_LIST FILE_LIST_LENGTH)
  set(out_string "")

  if(FILE_LIST_LENGTH LESS_EQUAL 0)
    message(FATAL_ERROR "FILE_LIST must contain at least one file")
  elseif(FILE_LIST_LENGTH EQUAL 1)
    if(arg_COMMENT)
      file(READ "${arg_FILE_LIST}" out_string)
    else()
      install(
        FILES "${arg_FILE_LIST}"
        DESTINATION "${arg_DESTINATION}"
        RENAME copyright)
      return()
    endif()
  else()
    foreach(file_item IN LISTS arg_FILE_LIST)
      if(NOT EXISTS "${file_item}")
        message(
          FATAL_ERROR
            "\n${CMAKE_CURRENT_FUNCTION} was passed a non-existing path: ${file_item}\n"
        )
      endif()

      get_filename_component(file_name "${file_item}" NAME)
      file(READ "${file_item}" file_contents)

      string(APPEND out_string "${file_name}:\n\n${file_contents}\n\n")
    endforeach()
  endif()

  if(arg_COMMENT)
    string(PREPEND out_string "${arg_COMMENT}\n\n")
  endif()

  string(RANDOM random_suffix)
  set(_cache_dir ${CMAKE_BINARY_DIR}/${CMAKE_CURRENT_FUNCTION}/copyright)

  file(WRITE "${_cache_dir}/copyright_${random_suffix}" "${out_string}")
  install(
    FILES "${_cache_dir}/copyright_${random_suffix}"
    DESTINATION "${arg_DESTINATION}"
    RENAME copyright)
endfunction()
