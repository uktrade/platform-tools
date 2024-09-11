#!/bin/bash

set -e

echo -e "\n\nBuild and install platform-helper\n"

cd "${CODEBUILD_SRC_DIR}"

echo -e "\nBuild platform-helper\n"
poetry build --no-interaction --format sdist --no-ansi

echo -e "\nInstall platform-helper\n"
pip install "dist/$(ls -t1 dist | head -1)"

echo -e "\nCheck platform-helper --version\n"
platform-helper --version
