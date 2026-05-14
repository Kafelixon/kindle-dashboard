import os
import subprocess
import sys
from pathlib import Path

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext


class CMakeExtension(Extension):
    def __init__(self, name: str, sourcedir: str = "."):
        super().__init__(name, sources=[])
        self.sourcedir = Path(sourcedir).resolve()


class CMakeBuild(build_ext):
    def build_extension(self, ext: CMakeExtension) -> None:
        extdir = Path(self.get_ext_fullpath(ext.name)).parent.resolve()
        build_temp = Path(self.build_temp) / ext.name
        build_temp.mkdir(parents=True, exist_ok=True)

        config = "Debug" if self.debug else "Release"
        generator = os.environ.get("CMAKE_GENERATOR", "Ninja")
        cmake_args = [
            f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={extdir}",
            f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_{config.upper()}={extdir}",
            f"-DPython_EXECUTABLE={self.get_executable()}",
            f"-DCMAKE_BUILD_TYPE={config}",
        ]

        try:
            import pybind11
        except ImportError:
            pass
        else:
            cmake_args.append(f"-Dpybind11_DIR={pybind11.get_cmake_dir()}")

        if generator:
            cmake_args.extend(["-G", generator])

        subprocess.check_call(["cmake", "-S", str(ext.sourcedir), "-B", str(build_temp), *cmake_args])
        subprocess.check_call(["cmake", "--build", str(build_temp), "--config", config])

    def get_executable(self) -> str:
        return os.environ.get("PYTHON", sys.executable)


setup(
    ext_modules=[CMakeExtension("kindle_dashboard._dither")],
    cmdclass={"build_ext": CMakeBuild},
)
