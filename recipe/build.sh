#!/usr/bin/env bash
set -euxo pipefail

cd "${SRC_DIR}"
"${PYTHON}" -m pip install . --no-build-isolation --no-deps -vv
