#!/bin/bash

set -e

cd "${CODEBUILD_SRC_DIR}"

echo -e "\nBuild and install platform-helper"
poetry build --no-interaction --format sdist --no-ansi
mkdir ./build-tools
pip install --target ./build-tools --quiet "dist/$(ls -t1 dist | head -1)"
export PATH="${CODEBUILD_SRC_DIR}/build-tools/bin:$PATH"
export PYTHONPATH="${CODEBUILD_SRC_DIR}/build-tools"
platform-helper --version
