#!/bin/bash

set -e

cd "${CODEBUILD_SRC_DIR}"

echo -e "\nBuild and install platform-helper"
poetry build --no-interaction --format sdist --no-ansi
mkdir ./build-tools
cd ./build-tools
pip install --target . "dist/$(ls -t1 dist | head -1)"
platform-helper --version
