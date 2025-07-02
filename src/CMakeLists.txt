file(
  GLOB _sub_dirs
  RELATIVE ${CMAKE_CURRENT_SOURCE_DIR}
  ${CMAKE_CURRENT_SOURCE_DIR}/*)

foreach(_sub_dir ${_sub_dirs})
  if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${_sub_dir}/CMakeLists.txt")
    add_subdirectory(${_sub_dir})
  endif()
endforeach()

unset(_sub_dirs)
