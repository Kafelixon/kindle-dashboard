cmake_minimum_required(VERSION 3.20)
project(kindle_dashboard_renderer LANGUAGES CXX)

set(PYBIND11_FINDPYTHON ON)
find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(_dither cpp/dither.cpp)
target_compile_features(_dither PRIVATE cxx_std_17)
install(TARGETS _dither DESTINATION kindle_dashboard)
