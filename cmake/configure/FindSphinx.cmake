#[[
This provides modules to configure sphinx.
]]
include(FindPackageHandleStandardArgs)

macro(_Sphinx_find_executable _exe)
  # Convert the executable name to uppercase
  string(TOUPPER "${_exe}" _uc)

  # Find the Sphinx executable sphinx-(build|quickstart)-3 x.x.x
  find_program(SPHINX_${_uc}_EXECUTABLE
               NAMES "sphinx-${_exe}-3" "sphinx-${_exe}" "sphinx-${_exe}.exe")

  if(SPHINX_${_uc}_EXECUTABLE)
    # Check the version of the Sphinx executable
    execute_process(
      COMMAND "${SPHINX_${_uc}_EXECUTABLE}" --version
      RESULT_VARIABLE _result
      OUTPUT_VARIABLE _output
      OUTPUT_STRIP_TRAILING_WHITESPACE)

    if(_result EQUAL 0 AND _output MATCHES " v?([0-9]+\\.[0-9]+\\.[0-9]+)$")
      set(SPHINX_${_uc}_VERSION "${CMAKE_MATCH_1}")
    endif()

    if(NOT TARGET Sphinx::${_exe})
      # Create an imported global target for the Sphinx executable
      add_executable(Sphinx::${_exe} IMPORTED GLOBAL)
      set_target_properties(
        Sphinx::${_exe} PROPERTIES IMPORTED_LOCATION
                                   "${SPHINX_${_uc}_EXECUTABLE}")
    endif()

    set(Sphinx_${_exe}_FOUND TRUE)
  else()
    set(Sphinx_${_exe}_FOUND FALSE)
  endif()

  unset(_uc)
endmacro()

macro(_Sphinx_find_module _name _module)
  # Convert _name to uppercase
  string(TOUPPER "${_name}" _Sphinx_uc)

  # Check if SPHINX_PYTHON_EXECUTABLE is available
  if(SPHINX_PYTHON_EXECUTABLE)
    # Execute the Sphinx Python module with the version argument
    execute_process(
      COMMAND ${SPHINX_PYTHON_EXECUTABLE} -m ${_module} --version
      RESULT_VARIABLE _result
      OUTPUT_VARIABLE _output
      OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET)

    # If the execution is successful
    if(_result EQUAL 0)
      # Extract the version number from the output
      if(_output MATCHES " v?([0-9]+\\.[0-9]+\\.[0-9]+)$")
        set(SPHINX_${_Sphinx_uc}_VERSION "${CMAKE_MATCH_1}")
      endif()

      # If the Sphinx target is not already defined
      if(NOT TARGET Sphinx::${_name})
        # Set the Sphinx executable and create an imported target
        set(SPHINX_${_Sphinx_uc}_EXECUTABLE
            "${SPHINX_PYTHON_EXECUTABLE} -m ${_module}")
        add_executable(Sphinx::${_name} IMPORTED GLOBAL)
        set_target_properties(
          Sphinx::${_name} PROPERTIES IMPORTED_LOCATION
                                      "${SPHINX_PYTHON_EXECUTABLE}")
      endif()

      # Set the Sphinx arguments and mark the module as found
      set(Sphinx_${_name}_ARGS -m ${_module})
      set(Sphinx_${_name}_FOUND TRUE)
    else()
      # If the execution is not successful, mark the module as not found
      set(Sphinx_${_name}_FOUND FALSE)
    endif()
  else()
    # If SPHINX_PYTHON_EXECUTABLE is not available, mark the module as not found
    set(Sphinx_${_name}_FOUND FALSE)
  endif()

  unset(_Sphinx_uc)
endmacro()

macro(_Sphinx_find_extension _ext)
  # Check if the Sphinx Python executable is available
  if(SPHINX_PYTHON_EXECUTABLE)
    # Use the Sphinx Python executable to import the extension module
    execute_process(COMMAND ${SPHINX_PYTHON_EXECUTABLE} -c "import ${_ext}"
                    RESULT_VARIABLE _result)

    # If the import is successful, set the extension as found
    if(_result EQUAL 0)
      set(Sphinx_${_ext}_FOUND TRUE)
    else()
      # If the import fails, set the extension as not found
      set(Sphinx_${_ext}_FOUND FALSE)
    endif()
  endif()
endmacro()

#
# Find sphinx-build and sphinx-quickstart.
#

# Find sphinx-build shim.
_sphinx_find_executable(build)

if(SPHINX_BUILD_EXECUTABLE)
  # Find sphinx-quickstart shim.
  _sphinx_find_executable(quickstart)

  # Locate Python executable
  if(CMAKE_HOST_WIN32)
    # script-build on Windows located under (when PIP is used): C:/Program
    # Files/PythonXX/Scripts
    # C:/Users/username/AppData/Roaming/Python/PythonXX/Scripts
    #
    # Python modules are installed under: C:/Program Files/PythonXX/Lib
    # C:/Users/username/AppData/Roaming/Python/PythonXX/site-packages
    #
    # To verify a given module is installed, use the Python base directory and
    # test if either Lib/module.py or site-packages/module.py exists.
    get_filename_component(_Sphinx_directory "${SPHINX_BUILD_EXECUTABLE}"
                           DIRECTORY)
    get_filename_component(_Sphinx_directory "${_Sphinx_directory}" DIRECTORY)

    if(EXISTS "${_Sphinx_directory}/python.exe")
      set(SPHINX_PYTHON_EXECUTABLE "${_Sphinx_directory}/python.exe")
    endif()

    unset(_Sphinx_directory)
  else()
    file(READ "${SPHINX_BUILD_EXECUTABLE}" _Sphinx_script)

    if(_Sphinx_script MATCHES "^#!([^\n]+)")
      string(STRIP "${CMAKE_MATCH_1}" _Sphinx_shebang)

      if(EXISTS "${_Sphinx_shebang}")
        set(SPHINX_PYTHON_EXECUTABLE "${_Sphinx_shebang}")
      endif()
    endif()

    unset(_Sphinx_script)
    unset(_Sphinx_shebang)
  endif()
endif()

if(NOT SPHINX_PYTHON_EXECUTABLE)
  # Python executable cannot be extracted from shim shebang or path if e.g.
  # virtual environments are used, fallback to find package. Assume the correct
  # installation is found, the setup is probably broken in more ways than one
  # otherwise.
  find_package(Python3 QUIET COMPONENTS Interpreter)

  if(TARGET Python3::Interpreter)
    set(SPHINX_PYTHON_EXECUTABLE ${Python3_EXECUTABLE})

    # Revert to "python -m sphinx" if shim cannot be found.
    if(NOT SPHINX_BUILD_EXECUTABLE)
      _sphinx_find_module(build sphinx)
      _sphinx_find_module(quickstart sphinx.cmd.quickstart)
    endif()
  endif()
endif()

#
# Verify components are available.
#
if(SPHINX_BUILD_VERSION)
  # Breathe is required for Exhale
  if("exhale" IN_LIST Sphinx_FIND_COMPONENTS AND NOT "breathe" IN_LIST
                                                 Sphinx_FIND_COMPONENTS)
    list(APPEND Sphinx_FIND_COMPONENTS "breathe")
  endif()

  foreach(_Sphinx_component IN LISTS Sphinx_FIND_COMPONENTS)
    if(_Sphinx_component STREQUAL "build")
      # Do nothing, sphinx-build is always required.
      continue()
    elseif(_Sphinx_component STREQUAL "quickstart")
      # Do nothing, sphinx-quickstart is optional, but looked up by default.
      continue()
    endif()

    _sphinx_find_extension(${_Sphinx_component})
  endforeach()

  unset(_Sphinx_component)

  #
  # Verify both executables are part of the Sphinx distribution.
  #
  if(SPHINX_QUICKSTART_VERSION AND NOT SPHINX_BUILD_VERSION STREQUAL
                                   SPHINX_QUICKSTART_VERSION)
    message(
      FATAL_ERROR
        "Versions for sphinx-build (${SPHINX_BUILD_VERSION}) "
        "and sphinx-quickstart (${SPHINX_QUICKSTART_VERSION}) " "do not match")
  endif()
endif()

find_package_handle_standard_args(
  Sphinx
  VERSION_VAR SPHINX_BUILD_VERSION
  REQUIRED_VARS SPHINX_BUILD_EXECUTABLE SPHINX_BUILD_VERSION
  HANDLE_COMPONENTS)

# Generate a conf.py template file using sphinx-quickstart.
#
# sphinx-quickstart allows for quiet operation and a lot of settings can be
# specified as command line arguments, therefore its not required to parse the
# generated conf.py.
function(_sphinx_generate_conf_py _target _cachedir)
  if(NOT TARGET Sphinx::quickstart)
    message(FATAL_ERROR "sphinx-quickstart is not available, needed by"
                        "sphinx_add_docs for target ${_target}")
  endif()

  if(NOT DEFINED SPHINX_PROJECT)
    set(SPHINX_PROJECT ${PROJECT_NAME})
  endif()

  if(NOT DEFINED SPHINX_AUTHOR)
    set(SPHINX_AUTHOR "${SPHINX_PROJECT} committers")
  endif()

  if(NOT DEFINED SPHINX_COPYRIGHT)
    string(TIMESTAMP "%Y, ${SPHINX_AUTHOR}" SPHINX_COPYRIGHT)
  endif()

  if(NOT DEFINED SPHINX_VERSION)
    set(SPHINX_VERSION "${CMAKE_PROJECT_VERSION}")
  endif()

  if(NOT DEFINED SPHINX_RELEASE)
    set(SPHINX_RELEASE "${CMAKE_PROJECT_VERSION}")
  endif()

  if(NOT DEFINED SPHINX_LANGUAGE)
    set(SPHINX_LANGUAGE "en")
  endif()

  if(NOT DEFINED SPHINX_MASTER)
    set(SPHINX_MASTER "index")
  endif()

  set(_known_exts
      autodoc
      doctest
      intersphinx
      todo
      coverage
      imgmath
      mathjax
      ifconfig
      viewcode
      githubpages)

  if(DEFINED SPHINX_EXTENSIONS)
    foreach(_ext ${SPHINX_EXTENSIONS})
      set(_is_known_ext FALSE)

      foreach(_known_ext ${_known_exsts})
        if(_ext STREQUAL _known_ext)
          set(_opts "${opts} --ext-${_ext}")
          set(_is_known_ext TRUE)
          break()
        endif()
      endforeach()

      if(NOT _is_known_ext)
        if(_exts)
          set(_exts "${_exts},${_ext}")
        else()
          set(_exts "${_ext}")
        endif()
      endif()
    endforeach()
  endif()

  if(_exts)
    set(_exts "--extensions=${_exts}")
  endif()

  set(_templatedir "${CMAKE_CURRENT_BINARY_DIR}/${_target}.template")
  file(MAKE_DIRECTORY "${_templatedir}")
  string(REPLACE " " ";" _Sphinx_executable ${SPHINX_QUICKSTART_EXECUTABLE})
  message("_templatedir:${_templatedir}")
  message("_Sphinx_executable:${_Sphinx_executable}")
  message("SPHINX_PROJECT:${SPHINX_PROJECT}")
  message("SPHINX_AUTHOR:${SPHINX_AUTHOR}")
  message("SPHINX_VERSION:${SPHINX_VERSION}")
  message("_opts:${_opts}")
  message("_exts:${_exts}")
  execute_process(
    COMMAND
      ${_Sphinx_executable} -q --no-makefile --no-batchfile -p
      "${SPHINX_PROJECT}" -a "${SPHINX_AUTHOR}" -v "${SPHINX_VERSION}" -r
      "${SPHINX_RELEASE}" -l "${SPHINX_LANGUAGE}" --master "${SPHINX_MASTER}"
      ${_opts} ${_exts} "${_templatedir}"
    RESULT_VARIABLE _result
    OUTPUT_QUIET)
  unset(_Sphinx_executable)

  if(_result EQUAL 0 AND EXISTS "${_templatedir}/conf.py")
    file(COPY "${_templatedir}/conf.py" DESTINATION "${_cachedir}")
  endif()

  file(REMOVE_RECURSE "${_templatedir}")

  if(NOT _result EQUAL 0 OR NOT EXISTS "${_cachedir}/conf.py")
    message(FATAL_ERROR "Sphinx configuration file not generated for "
                        "target ${_target}")
  endif()
endfunction()

function(sphinx_add_docs _target)
  # Set options
  set(_opts ALL)
  set(_single_opts BUILDER OUTPUT_DIRECTORY SOURCE_DIRECTORY CONF_FILE
                   BREATH_DEBUG)
  set(_multi_opts BREATHE_PROJECTS EXTRA_ARGS)
  cmake_parse_arguments(PARSE_ARGV 0 "arg" "${_opts}" "${_single_opts}"
                        "${_multi_opts}")

  unset(SPHINX_BREATHE_PROJECTS)

  # Check if required arguments are provided
  if(NOT arg_BUILDER)
    message(FATAL_ERROR "Sphinx builder not specified for target ${_target}")
  elseif(NOT arg_SOURCE_DIRECTORY)
    message(
      FATAL_ERROR "Sphinx source directory not specified for target ${_target}")
  else()
    # Check if source directory is absolute or relative
    if(NOT IS_ABSOLUTE "${arg_SOURCE_DIRECTORY}")
      get_filename_component(_sourcedir "${arg_SOURCE_DIRECTORY}" ABSOLUTE)
    else()
      set(_sourcedir "${arg_SOURCE_DIRECTORY}")
    endif()

    # Check if source directory exists
    if(NOT IS_DIRECTORY "${_sourcedir}")
      message(FATAL_ERROR "Sphinx source directory '${_sourcedir}' for"
                          "target ${_target} does not exist")
    endif()
  endif()

  # Set builder and output directory
  set(_builder "${arg_BUILDER}")

  if(arg_OUTPUT_DIRECTORY)
    set(_outputdir "${arg_OUTPUT_DIRECTORY}")
  else()
    set(_outputdir "${CMAKE_CURRENT_BINARY_DIR}/${_target}/${_builder}")
  endif()

  # Check if breathe projects are specified
  if(arg_BREATHE_PROJECTS)
    if(NOT Sphinx_breathe_FOUND)
      message(FATAL_ERROR "Sphinx extension 'breathe' is not available. Needed"
                          "by sphinx_add_docs for target ${_target}")
    endif()

    # Add 'breathe' extension to SPHINX_EXTENSIONS
    list(APPEND SPHINX_EXTENSIONS breathe)

    # Iterate through each breathe project
    foreach(_doxygen_target ${arg_BREATHE_PROJECTS})
      if(TARGET ${_doxygen_target})
        list(APPEND _depends ${_doxygen_target})

        # Check if Doxyfile exists for the doxygen target
        get_target_property(_dir ${_doxygen_target} BINARY_DIR)
        set(_doxyfile "${_dir}/Doxyfile.${_doxygen_target}")

        # Verify the existence of Doxyfile
        if(NOT EXISTS "${_doxyfile}")
          message(
            FATAL_ERROR
              "Target ${_doxygen_target} is not a Doxygen"
              "target, needed by sphinx_add_docs for target" "${_target}")
        endif()

        # Read the Doxyfile, verify XML generation is enabled and retrieve the
        # output directory.
        file(READ "${_doxyfile}" _contents)

        if(NOT _contents MATCHES "GENERATE_XML *= *YES")
          message(
            FATAL_ERROR
              "Doxygen target ${_doxygen_target} does not"
              "generate XML, needed by sphinx_add_docs for" "target ${_target}")
        elseif(_contents MATCHES "OUTPUT_DIRECTORY *= *([^ ][^\n]*)")
          # Retrieve the output directory from Doxyfile
          string(STRIP "${CMAKE_MATCH_1}" _dir)
          set(_name "${_doxygen_target}")
          set(_dir "${_dir}/xml")
        else()
          message(
            FATAL_ERROR
              "Cannot parse Doxyfile generated by Doxygen"
              "target ${_doxygen_target}, needed by"
              "sphinx_add_docs for target ${_target}")
        endif()
      elseif(_doxygen_target MATCHES "([^: ]+) *: *(.*)")
        set(_name "${CMAKE_MATCH_1}")
        string(STRIP "${CMAKE_MATCH_2}" _dir)
      endif()

      # Add breathe project to the list
      if(_name AND _dir)
        if(_breathe_projects)
          set(_breathe_projects
              "${_breathe_projects}, \"${_name}\": \"${_dir}\"")
        else()
          set(_breathe_projects "\"${_name}\": \"${_dir}\"")
        endif()

        # Set the first breathe project as the default project
        if(NOT _breathe_default_project)
          set(_breathe_default_project "${_name}")
        endif()
      endif()
    endforeach()
  endif()

  # Set BREATH_DEBUG based on the value of arg_BREATH_DEBUG
  if(arg_BREATH_DEBUG)
    set(BREATH_DEBUG ${arg_BREATH_DEBUG})
  else()
    set(BREATH_DEBUG False)
  endif()

  # Set the path for the cache directory
  set(_cachedir "${CMAKE_CURRENT_BINARY_DIR}/${_target}.cache")
  file(MAKE_DIRECTORY "${_cachedir}")

  # Check if arg_CONF_FILE exists and configure the project accordingly
  if(arg_CONF_FILE AND EXISTS ${arg_CONF_FILE})
    # Set BREATHE_DEFAULT_PROJECT and BREATHE_PROJECTS
    set(BREATHE_DEFAULT_PROJECT ${_breathe_default_project})
    set(BREATHE_PROJECTS ${_breathe_projects})

    # Copy the arg_CONF_FILE to the cache directory and copy all docs files to
    # the cache directory
    file(COPY ${arg_CONF_FILE} DESTINATION ${_cachedir})
    file(GLOB all_docs_files ${_sourcedir}/*)
    file(COPY ${all_docs_files} DESTINATION ${_cachedir})
  else()
    # Create the _static directory in the cache directory
    file(MAKE_DIRECTORY "${_cachedir}/_static")

    # Generate the conf.py file using _sphinx_generate_conf_py function
    _sphinx_generate_conf_py(${_target} "${_cachedir}")
  endif()

  file(READ "${_sourcedir}/conf.py" _conf_contents)

  # Append breathe_projects and breathe_default_project to conf.py if
  # _breathe_projects is set
  if(_breathe_projects AND NOT _conf_contents MATCHES "breathe_projects *= *{")
    # If No breathe_projects is found, add it to the conf.py file and check
    # breathe_default_project.
    file(
      APPEND "${_cachedir}/conf.py"
      "\n# -- breath configuration ----------------------------------------------------\n"
      "\nbreathe_projects = { ${_breathe_projects} }")

    if(NOT _conf_contents MATCHES "breathe_default_project *= *")
      file(APPEND "${_cachedir}/conf.py"
           "\nbreathe_default_project = '${_breathe_default_project}'")
    endif()

    if(NOT _conf_contents MATCHES "breathe_debug_trace_directives *= *")
      file(APPEND "${_cachedir}/conf.py"
           "\nbreathe_debug_trace_directives = ${BREATH_DEBUG}\n")
    endif()

    set(_conf_dir "${_cachedir}")
  else()
    # If breathe_projects is found, use sourcedir as _cachedir for use user's
    # conf.py provided and warn if breathe_default_project is missing.
    set(_conf_dir "${_sourcedir}")

    if(NOT _conf_contents MATCHES "breathe_default_project *= *")
      message(WARNING "breathe_default_project is missing in conf.py")
    endif()
  endif()

  # Replace spaces with semicolons in SPHINX_BUILD_EXECUTABLE
  string(REPLACE " " ";" _Sphinx_executable ${SPHINX_BUILD_EXECUTABLE})

  # Handle the ALL option
  unset(_all)

  if(${arg_ALL})
    set(_all ALL)
  endif()

  # Add a custom target with the specified dependencies
  add_custom_target(
    ${_target}
    ${_all}
    COMMAND ${CMAKE_COMMAND} -E rm -rf "${_outputdir}"
    COMMAND ${_Sphinx_executable} ${arg_EXTRA_ARGS} -b ${_builder} -c
            "${_conf_dir}" "${_sourcedir}" "${_outputdir}"
    DEPENDS ${_depends})

  unset(_Sphinx_executable)
endfunction()
