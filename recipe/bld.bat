@echo off

cmake -S "%SRC_DIR%" -B build -G Ninja ^
  -DCMAKE_BUILD_TYPE=Release ^
  -DCMAKE_INSTALL_PREFIX="%SP_DIR%" ^
  -DPYTHON_EXECUTABLE="%PYTHON%" ^
  -DPython_EXECUTABLE="%PYTHON%"
if errorlevel 1 exit 1

cmake --build build
if errorlevel 1 exit 1

cmake --install build
if errorlevel 1 exit 1

cd /d "%SRC_DIR%"
"%PYTHON%" -m pip install . --no-build-isolation --no-deps -vv
if errorlevel 1 exit 1
