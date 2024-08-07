#!/bin/bash

set -e

cd "${CODEBUILD_SRC_DIR}"

echo -e "\nBuild and install platform-helper"
mkdir ./build-tools
export PATH="./build-tools/bin:$PATH"
export PYTHONPATH="./build-tools"

pip install --target ./build-tools poetry

poetry install
poetry build --no-interaction --format sdist --no-ansi

pip install --target ./build-tools "dist/$(ls -t1 dist | head -1)"

ls -LR ./build-tools

platform-helper --version
