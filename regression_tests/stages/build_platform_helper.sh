#!/bin/bash

set -e

cd "${CODEBUILD_SRC_DIR}"

echo -e "\nBuild and install platform-helper"
mkdir ./build-tools
pip install --target ./build-tools poetry
export PATH="${CODEBUILD_SRC_DIR}/build-tools/bin:$PATH"
export PYTHONPATH="${CODEBUILD_SRC_DIR}/build-tools"
poetry build --no-interaction --format sdist --no-ansi
pip install --target ./build-tools "dist/$(ls -t1 dist | head -1)"
platform-helper --version
