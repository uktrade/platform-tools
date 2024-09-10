#!/bin/bash

set -e

echo -e "\n\nBuild and install platform-helper\n"

cd "${CODEBUILD_SRC_DIR}"

poetry build --no-interaction --format sdist --no-ansi
pip install "dist/$(ls -t1 dist | head -1)"
platform-helper --version
