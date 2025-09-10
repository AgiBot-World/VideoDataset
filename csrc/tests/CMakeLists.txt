find_package(Catch2 CONFIG REQUIRED)

include(Catch)

file(GLOB files "*.cpp")

foreach(_file ${files})
  get_filename_component(file_basename ${_file} NAME_WE)
  add_executable(${file_basename} ${_file})
  target_link_libraries(${file_basename} PRIVATE Catch2::Catch2WithMain)
  target_link_libraries(${file_basename} PRIVATE ${target_name_internal})
  target_link_libraries(${file_basename} PRIVATE pybind11::embed)
  warn_target(${file_basename})
  harden_target(${file_basename})
  sanitize_target(${file_basename})
  catch_discover_tests(${file_basename})
endforeach()
