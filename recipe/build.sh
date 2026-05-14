#!/usr/bin/env bash
set -euxo pipefail

cmake -S "${SRC_DIR}" -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="${SP_DIR}" \
  -DPYTHON_EXECUTABLE="${PYTHON}" \
  -DPython_EXECUTABLE="${PYTHON}"

cmake --build build
cmake --install build

cd "${SRC_DIR}"
"${PYTHON}" -m pip install . --no-build-isolation --no-deps -vv
