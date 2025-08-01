set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 CONFIG REQUIRED)

find_package(dlpack CONFIG REQUIRED)

find_package(Python REQUIRED COMPONENTS Interpreter Development)

find_package(PkgConfig REQUIRED)

pkg_check_modules(FFMPEG REQUIRED libavformat libavcodec libavutil
                  libswresample)

set(target_name _decoder)
set(target_name_internal ${target_name}_internal)

file(GLOB_RECURSE ${target_name_internal}_srcs "src/*.cpp")
file(GLOB_RECURSE ${target_name_internal}_hdrs "include/*.hpp" "include/*.h")

add_library(${target_name_internal} OBJECT)
warn_target(${target_name_internal})
harden_target(${target_name_internal})
sanitize_target(${target_name_internal})

generate_git_header(VERSION_NAMESPACE_PREFIX ${target_name})

target_sources(${target_name_internal} PRIVATE ${${target_name_internal}_srcs}
                                               ${${target_name_internal}_hdrs})

target_include_interface_directories(
  ${target_name_internal} ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${CMAKE_CURRENT_BINARY_DIR}/git_version ${FFMPEG_INCLUDE_DIRS}
  ${CMAKE_CUDA_TOOLKIT_INCLUDE_DIRECTORIES})

target_link_libraries(
  ${target_name_internal}
  PUBLIC nvcuvid cuda ${FFMPEG_LIBRARIES} dlpack::dlpack Python::Python
         pybind11::headers)

pybind11_add_module(${target_name} MODULE pybind/bind.cpp)
warn_target(${target_name})
harden_target(${target_name})
sanitize_target(${target_name})

target_link_libraries(${target_name} PRIVATE ${target_name_internal}
                                             pybind11::module)

find_program(PYBIND11_STUBGEN pybind11-stubgen)
if(PYBIND11_STUBGEN)
  add_custom_command(
    TARGET ${target_name}
    POST_BUILD
    COMMAND
      ${CMAKE_COMMAND} -E env
      "PYTHONPATH=$<TARGET_FILE_DIR:${target_name}>:$ENV{PYTHONPATH}"
      ${PYBIND11_STUBGEN} -o "${CMAKE_SOURCE_DIR}/src/videodataset"
      --ignore-all-errors ${target_name}
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    COMMENT "Generating .pyi stubs for _decoder")
endif()

install(TARGETS ${target_name} DESTINATION ${CMAKE_PROJECT_NAME})

install_dependency(TARGETS ${target_name} DEPENDS_DESTINATION
                   ${CMAKE_PROJECT_NAME})

if(BUILD_TESTING)
  message(STATUS "Enabling testing")
  add_test_subdirectory(tests)
endif()
