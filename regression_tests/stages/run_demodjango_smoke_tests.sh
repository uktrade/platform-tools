#!/bin/bash

set -e

cd "${CODEBUILD_SRC_DIR}/demodjango"

echo -e "\nInstall dependencies"
poetry install

echo -e "\nRun smoke tests"
<<<<<<< HEAD
./smoke_tests.sh ${TARGET_ENVIRONMENT}
=======
./tests/browser/run.sh toolspr smoke
>>>>>>> main
