#!/bin/bash

set -e

cd "${CODEBUILD_SRC_DIR}/demodjango"

echo -e "\nInstall dependencies"
poetry install

echo -e "\nRun smoke tests"
./tests/browser/run.sh toolspr smoke
