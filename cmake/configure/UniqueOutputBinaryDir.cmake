#[[
Sets the output directories for the build artifacts in a CMake project.

Example Usage:
```cmake
include(UniqueOutputBinaryDir)
```

Inputs:
- None

Flow:
1. Includes the GNUInstallDirs module, which provides the GNU install standard paths.
2. Sets the `CMAKE_ARCHIVE_OUTPUT_DIRECTORY` variable to `${CMAKE_BINARY_DIR}/${CMAKE_INSTALL_LIBDIR}`, specifying the output directory for library archives.
3. Sets the `CMAKE_LIBRARY_OUTPUT_DIRECTORY` variable to `${CMAKE_BINARY_DIR}/${CMAKE_INSTALL_LIBDIR}`, specifying the output directory for shared libraries.
4. Sets the `CMAKE_RUNTIME_OUTPUT_DIRECTORY` variable to `${CMAKE_BINARY_DIR}/${CMAKE_INSTALL_BINDIR}`, specifying the output directory for executables.

Outputs:
- None
]]

# GNU install standard
enable_language(C)
enable_language(CXX)
include(GNUInstallDirs)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/${CMAKE_INSTALL_LIBDIR})
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/${CMAKE_INSTALL_LIBDIR})
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/${CMAKE_INSTALL_BINDIR})
