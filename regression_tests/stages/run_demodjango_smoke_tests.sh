#!/bin/bash

set -e

cd "${CODEBUILD_SRC_DIR}/demodjango"

echo -e "\nInstall dependencies"
poetry install

echo -e "\nRun smoke tests"
./smoke_tests.sh ${TARGET_ENVIRONMENT}
