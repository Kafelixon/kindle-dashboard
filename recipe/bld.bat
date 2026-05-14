@echo off

cd /d "%SRC_DIR%"
"%PYTHON%" -m pip install . --no-build-isolation --no-deps -vv
if errorlevel 1 exit 1
