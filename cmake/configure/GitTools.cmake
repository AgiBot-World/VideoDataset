#[[
This module provides some git stuffs.

]]

include_guard(GLOBAL)

#[[
A function to generate a git version header using the current
project git meta. It requires the following variables to be set:
  - CMAKE_PROJECT_GIT_COMMIT*: git commit information (see below)
  - CMAKE_PROJECT_VERSION: project version number (major.minor.patch.tweak)
  - CMAKE_PROJECT_VERSION_<MAJOR|MINOR|PATCH|TWEAK>: project version numbers (major, minor, patch, tweak)

Arguments:
  CONFIGURE_HEADER_FILE - git header configuration content.
    Default to ${CMAKE_CURRENT_BINARY_DIR}/git_version_template/_version.hpp.in (optional)
  DESTINATION - git header destination to generate.
    Default to ${CMAKE_CURRENT_BINARY_DIR}/git_version/_version.hpp (optional)
  VERSION_NAMESPACE_PREFIX - namespace prefix for the generated cxx header.
    Default to ${CMAKE_PROJECT_NAME} (optional)

Example:

  include(GitTools)
  add_library(header INTERFACE)
  generate_git_header(VERSION_NAMESPACE_PREFIX header)
  target_include_interface_directories(header ${CMAKE_CURRENT_BINARY_DIR}/git_version)
  install_target(
    NAME
    header
    VERSION
    ${CMAKE_PROJECT_VERSION}
    TARGETS
    header
    INCLUDES
    ${CMAKE_CURRENT_BINARY_DIR}/git_version/)

See also:
  - https://raw.githubusercontent.com/andrew-hardin/cmake-git-version-tracking/master/git.h
]]
function(generate_git_header)
  set(_opts)
  set(_single_opts CONFIGURE_HEADER_FILE DESTINATION VERSION_NAMESPACE_PREFIX)
  set(_multi_opts)
  cmake_parse_arguments(arg "${_opts}" "${_single_opts}" "${_multi_opts}"
                        ${ARGN})

  if(NOT arg_DESTINATION)
    set(arg_DESTINATION ${CMAKE_CURRENT_BINARY_DIR}/git_version/_version.hpp)
  endif()

  if(NOT arg_VERSION_NAMESPACE_PREFIX)
    set(arg_VERSION_NAMESPACE_PREFIX ${CMAKE_PROJECT_NAME})
  endif()

  if(NOT arg_CONFIGURE_HEADER_FILE)

    # Define default template variables
    if(NOT CMAKE_PROJECT_GIT_COMMIT_DIRTY)
      set(CMAKE_PROJECT_GIT_COMMIT_DIRTY
          0
          CACHE INTERNAL "")
    endif()

    set(_configure_git_header_content
        "#pragma once
// git.h
// https://raw.githubusercontent.com/andrew-hardin/cmake-git-version-tracking/master/git.h
//
// Released under the MIT License.
// https://raw.githubusercontent.com/andrew-hardin/cmake-git-version-tracking/master/LICENSE

#include <stdbool.h>

#ifdef __cplusplus
#define GIT_EXTERN_C_BEGIN                extern \"C\" {
#define GIT_VERSION_TRACKING_EXTERN_C_END }
#else
#define GIT_EXTERN_C_BEGIN
#define GIT_VERSION_TRACKING_EXTERN_C_END
#endif

// Don't mangle the C function names if included in a CXX file.
GIT_EXTERN_C_BEGIN

/// The commit project version.
inline const char* git_ProjectVersion() {
    return R\"(@CMAKE_PROJECT_VERSION@)\"\;
}

/// The commit project version major.
inline const char* git_ProjectVersionMajor() {
    return R\"(@CMAKE_PROJECT_VERSION_MAJOR@)\"\;
}

/// The commit project version minor.
inline const char* git_ProjectVersionMinor() {
    return R\"(@CMAKE_PROJECT_VERSION_MINOR@)\"\;
}

/// The commit project version patch.
inline const char* git_ProjectVersionPatch() {
    return R\"(@CMAKE_PROJECT_VERSION_PATCH@)\"\;
}

/// The commit project version tweak.
inline const char* git_ProjectVersionTweak() {
    return R\"(@CMAKE_PROJECT_VERSION_TWEAK@)\"\;
}

/// Were there any uncommitted changes that won't be reflected
/// in the CommitID?
inline bool git_AnyUncommittedChanges() {
    return @CMAKE_PROJECT_GIT_COMMIT_DIRTY@ == 1\;
}

/// The commit author's name.
inline const char* git_AuthorName() {
    return R\"(@CMAKE_PROJECT_GIT_COMMIT_AUTHOR_NAME@)\"\;
}

/// The commit author's email.
inline const char* git_AuthorEmail() {
    return R\"(@CMAKE_PROJECT_GIT_COMMIT_AUTHOR_EMAIL@)\"\;
}

/// The commit last tag.
inline const char* git_CommitTag() {
    return R\"(@CMAKE_PROJECT_GIT_COMMIT_TAG@)\"\;
}

/// The commit number since last tag.
inline const char* git_CommitTagRevision() {
    return R\"(@CMAKE_PROJECT_GIT_COMMIT_TAG_REVISION@)\"\;
}

/// The commit number.
inline const char* git_CommitRevision() {
    return R\"(@CMAKE_PROJECT_GIT_COMMIT_REVISION@)\"\;
}

/// The commit number of the day.
inline const char* git_CommitDateRevision() {
    return R\"(@CMAKE_PROJECT_GIT_COMMIT_DATE_REVISION@)\"\;
}

/// The commit SHA1.
inline const char* git_CommitSHA1() {
    return R\"(@CMAKE_PROJECT_GIT_COMMIT_HASH@)\"\;
}

/// The commit short SHA1.
inline const char* git_CommitSHA1Short() {
    return R\"(@CMAKE_PROJECT_GIT_COMMIT_HASH_SHORT@)\"\;
}

/// The commit date.
inline const char* git_CommitDate() {
    return R\"(@CMAKE_PROJECT_GIT_COMMIT_AUTHOR_DATE@)\"\;
}

/// The commit time.
inline const char* git_CommitTime() {
    return R\"(@CMAKE_PROJECT_GIT_COMMIT_AUTHOR_TIME@)\"\;
}

/// The commit TZ.
inline const char* git_CommitTZ() {
    return R\"(@CMAKE_PROJECT_GIT_COMMIT_AUTHOR_TZ@)\"\;
}

/// The commit subject.
inline const char* git_CommitSubject() {
    return R\"(@CMAKE_PROJECT_GIT_COMMIT_SUBJECT@)\"\;
}

/// The commit body.
inline const char* git_CommitBody() {
    return R\"(@CMAKE_PROJECT_GIT_COMMIT_BODY@)\"\;
}

/// The commit describe.
inline const char* git_Describe() {
    return R\"(@CMAKE_PROJECT_GIT_COMMIT_DESCRIBE@)\"\;
}

GIT_VERSION_TRACKING_EXTERN_C_END
#undef GIT_EXTERN_C_BEGIN
#undef GIT_VERSION_TRACKING_EXTERN_C_END

#ifdef __cplusplus

/// This is a utility extension for C++ projects.
/// It provides a \"${arg_VERSION_NAMESPACE_PREFIX}\" namespace that wraps the
/// C methods in more(?) ergonomic types.
///
/// This is header-only in an effort to keep the
/// underlying static library C99 compliant.

// We really want to use std::string_view if it appears
// that the compiler will support it. If that fails,
// revert back to std::string.
#define GIT_VERSION_CPP_17_STANDARD 201703L
#if __cplusplus >= GIT_VERSION_CPP_17_STANDARD
#define GIT_VERSION_USE_STRING_VIEW 1
#else
#define GIT_VERSION_USE_STRING_VIEW 0
#endif

#if GIT_VERSION_USE_STRING_VIEW
#include <cstring>
#include <string_view>
#else
#include <string>
#endif

namespace ${arg_VERSION_NAMESPACE_PREFIX} {

#if GIT_VERSION_USE_STRING_VIEW
using StringOrView = std::string_view\;
#else
typedef std::string StringOrView\;
#endif

namespace internal {

/// Short-hand method for initializing a std::string or std::string_view given a C-style const char*.
inline const StringOrView InitString(const char* from_c_interface) {
#if GIT_VERSION_USE_STRING_VIEW
    return StringOrView{from_c_interface, std::strlen(from_c_interface)}\;
#else
    return std::string(from_c_interface)\;
#endif
}

} // namespace internal

inline const StringOrView& ProjectVersion() {
  static const StringOrView kValue = internal::InitString(git_ProjectVersion())\;
  return kValue\;
}
inline const StringOrView& ProjectVersionMajor() {
  static const StringOrView kValue = internal::InitString(git_ProjectVersionMajor())\;
  return kValue\;
}
inline const StringOrView& ProjectVersionMinor() {
  static const StringOrView kValue = internal::InitString(git_ProjectVersionMinor())\;
  return kValue\;
}
inline const StringOrView& ProjectVersionPatch() {
  static const StringOrView kValue = internal::InitString(git_ProjectVersionPatch())\;
  return kValue\;
}
inline const StringOrView& ProjectVersionTweak() {
  static const StringOrView kValue = internal::InitString(git_ProjectVersionTweak())\;
  return kValue\;
}
inline bool AnyUncommittedChanges() {
  static const bool kValue = git_AnyUncommittedChanges()\;
  return kValue\;
}
inline const StringOrView& AuthorName() {
    static const StringOrView kValue = internal::InitString(git_AuthorName())\;
    return kValue\;
}
inline const StringOrView AuthorEmail() {
    static const StringOrView kValue = internal::InitString(git_AuthorEmail())\;
    return kValue\;
}
inline const StringOrView CommitTag() {
  static const StringOrView kValue = internal::InitString(git_CommitTag())\;
  return kValue\;
}
inline const StringOrView CommitTagRevision() {
  static const StringOrView kValue = internal::InitString(git_CommitTagRevision())\;
  return kValue\;
}
inline const StringOrView CommitRevision() {
  static const StringOrView kValue = internal::InitString(git_CommitRevision())\;
  return kValue\;
}
inline const StringOrView CommitDateRevision() {
  static const StringOrView kValue = internal::InitString(git_CommitDateRevision())\;
  return kValue\;
}
inline const StringOrView CommitSHA1() {
    static const StringOrView kValue = internal::InitString(git_CommitSHA1())\;
    return kValue\;
}
inline const StringOrView CommitSHA1Short() {
  static const StringOrView kValue = internal::InitString(git_CommitSHA1Short())\;
  return kValue\;
}
inline const StringOrView CommitDate() {
    static const StringOrView kValue = internal::InitString(git_CommitDate())\;
    return kValue\;
}
inline const StringOrView CommitTime() {
  static const StringOrView kValue = internal::InitString(git_CommitTime())\;
  return kValue\;
}
inline const StringOrView CommitTZ() {
  static const StringOrView kValue = internal::InitString(git_CommitTZ())\;
  return kValue\;
}
inline const StringOrView CommitSubject() {
    static const StringOrView kValue = internal::InitString(git_CommitSubject())\;
    return kValue\;
}
inline const StringOrView CommitBody() {
    static const StringOrView kValue = internal::InitString(git_CommitBody())\;
    return kValue\;
}
inline const StringOrView Describe() {
    static const StringOrView kValue = internal::InitString(git_Describe())\;
    return kValue\;
}

} // namespace ${arg_VERSION_NAMESPACE_PREFIX}

// Cleanup our defines to avoid polluting.
#undef GIT_VERSION_USE_STRING_VIEW
#undef GIT_VERSION_CPP_17_STANDARD

#endif // __cplusplus
")

    set(arg_CONFIGURE_HEADER_FILE
        ${CMAKE_CURRENT_BINARY_DIR}/git_version_template/_version.hpp.in)
    file(WRITE ${arg_CONFIGURE_HEADER_FILE} ${_configure_git_header_content})
  endif()

  configure_file("${arg_CONFIGURE_HEADER_FILE}" "${arg_DESTINATION}" @ONLY)

  get_filename_component(_destination_dir ${arg_DESTINATION} DIRECTORY)

  string(REPLACE "${CMAKE_CURRENT_BINARY_DIR}" "" _binary_include_dir
                 "${_destination_dir}")
  string(REPLACE "${CMAKE_CURRENT_SOURCE_DIR}" "" _source_include_dir
                 "${_destination_dir}")

  if(NOT "${_binary_include_dir}" STREQUAL "${_destination_dir}")
    set(_include_dir_for_target
        "\${CMAKE_CURRENT_BINARY_DIR}${_binary_include_dir}")
  else()
    set(_include_dir_for_target
        "\${CMAKE_CURRENT_SOURCE_DIR}${_source_include_dir}")
  endif()

  message(
    STATUS
      "Generated a git-based version header including project metadata in ${arg_DESTINATION} from ${arg_CONFIGURE_HEADER_FILE}
  Usage:
    target_include_directories(${_include_dir_for_target})
    # or
    target_include_interface_directories(${_include_dir_for_target})")
endfunction()
