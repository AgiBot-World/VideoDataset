#[[
ProjectOptions.cmake - Defines project-specific options for CMake.
]]

set(CMAKE_CXX_STANDARD
    20
    CACHE STRING "C++ standard")
set(CMAKE_CXX_STANDARD_REQUIRED
    ON
    CACHE BOOL "C++ standard required")
set(CMAKE_CXX_EXTENSIONS
    OFF
    CACHE BOOL "C++ extensions")

# ##############################################################################
# Sanitizer - cmake-modules/build/Sanitizer.cmake
# ##############################################################################

set(USE_SANITIZER
    OFF
    CACHE BOOL "Enable sanitizer")

# ##############################################################################
# Valgrind - cmake-modules/test/Valgrind.cmake
# ##############################################################################

set(USE_VALGRIND
    OFF
    CACHE BOOL "Enable Valgrind")
set(USE_VALGRIND_OPTIONS
    --leak-check=full # Each individual leak will be shown in detail.
    --show-leak-kinds=all # Show all of "definite, indirect, possible,
                          # reachable" leak kinds in the "full" report.
    --gen-suppressions=all # gen suppress info automatically.
    --track-origins=yes # Favor useful output over speed. This tracks the
                        # origins of uninitialized values, which could be very
                        # useful for memory errors. Consider turning off if
                        # Valgrind is unacceptably slow.
    CACHE STRING "valgrind options.")

# ##############################################################################
# Clang-Tidy - cmake-modules/build/ClangTidy.cmake
# ##############################################################################

set(USE_CLANGTIDY
    OFF
    CACHE BOOL "Enable Clang-Tidy")

# ##############################################################################
# Cppcheck - cmake-modules/build/Cppcheck.cmake
# ##############################################################################

set(USE_CPPCHECK
    OFF
    CACHE BOOL "Enable Cppcheck")
set(USE_CPPCHECK_SUPPRESSION_FILE
    ${CMAKE_SOURCE_DIR}/.cppcheck-suppressions.txt
    CACHE STRING
          "Customize the path to the Cppcheck suppressions file of the project")

# ##############################################################################
# Hardening - cmake-modules/build/Hardening.cmake
# ##############################################################################

# Comment `-Wl,-z,nodlopen` for dlopen call
if(NOT MSVC)
  set(USE_HARDENING_FLAGS
      -D_GLIBCXX_ASSERTIONS # Enable assertions
      -U_FORTIFY_SOURCE # Disable stack protector
      -D_FORTIFY_SOURCE=3 # Enable stack protector
      -fstack-protector-strong # Enable stack protector
      -fcf-protection # Control Flow Guard
      -fstack-clash-protection # Control Flow Guard
      -Wimplicit-fallthrough # Enabled in compiler flags by default
      -fstrict-flex-arrays=3 # Enable strict array bounds
      -Wformat # Enabled in compiler flags by default
      -Wformat=2 # Enabled in compiler flags by default
      # -Wl,-z,nodlopen # Restrict dlopen(3) calls to shared objects
      -Wl,-z,noexecstack # Enable data execution prevention by marking stack
      # memory as non-executable
      -Wl,-z,relro # Mark relocation table entries resolved at load-time as
      # read-only
      -Wl,-z,now # Mark relocation table entries resolved at load-time as
      # read-only. It impacts startup performance
      "-fsanitize=undefined -fsanitize-minimal-runtime" # Enable minimal runtime
      # undefined behavior sanitizer
      -fno-delete-null-pointer-checks
      -fno-strict-overflow
      -fno-strict-aliasing
      -ftrivial-auto-var-init=zero
      -Wtrampolines # Enable trampolines(gcc only)
      -mbranch-protection=standard # Enable indirect branches(aarch64 only)
      CACHE STRING "Additional hardening compilation flags for GCC/Clang")

  set(USE_HARDENING_LINKS
      -fstack-protector-strong # Enable stack protector
      "-fsanitize=undefined -fsanitize-minimal-runtime"
      # -Wl,-z,nodlopen # Restrict dlopen(3) calls to shared objects
      -Wl,-z,noexecstack # Enable data execution prevention by marking stack
      # memory as non-executable
      -Wl,-z,relro # Mark relocation table entries resolved at load-time as
      # read-only
      -Wl,-z,now # Mark relocation table entries resolved at load-time as
      # read-only. It impacts startup performance
      CACHE STRING "Additional hardening linking flags for GCC/Clang")
endif()
