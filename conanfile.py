from __future__ import annotations

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class VideoDatasetConan(ConanFile):
    name = "videodataset"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("pybind11/2.13.6")
        if not self.conf.get("tools.build:skip_test", False):
            self.requires("catch2/3.8.1")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_TESTING"] = (
            "ON" if not self.conf.get("tools.build:skip_test") else "OFF"
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
