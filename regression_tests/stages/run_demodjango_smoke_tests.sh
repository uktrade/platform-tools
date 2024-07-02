#!/bin/bash

set -e

# Todo: Uncomment before merge or to run in CodeBuild or to re-clone locally
# echo -e "\nClone demodjango"
# git clone "${GIT_CLONE_BASE_URL}/demodjango.git"

cd "${CODEBUILD_SRC_DIR}/demodjango"
echo "Current demodjango branch/commit: $(git rev-parse --abbrev-ref HEAD)/$(git rev-parse HEAD)"

echo -e "\nInstall dependencies"
poetry install

echo -e "\nRun smoke tests"
./smoke_tests.sh ${TARGET_ENVIRONMENT}
