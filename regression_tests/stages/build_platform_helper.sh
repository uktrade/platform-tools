#!/bin/bash

set -e

cd "${CODEBUILD_SRC_DIR}"

echo -e "\nBuild and install platform-helper"
poetry build --no-interaction --format sdist --no-ansi
mkdir ./build-tools
pip install --target ./build-tools --quiet "dist/$(ls -t1 dist | head -1)"
export "PATH=./build-tools/bin:$PATH"
platform-helper --version
