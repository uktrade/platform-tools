#!/bin/bash

set -e

echo -e "\nClone demodjango"

git clone "${GIT_CLONE_BASE_URL}/demodjango.git"

cd "${CODEBUILD_SRC_DIR}/demodjango"
echo -e "\nCurrent demodjango branch/commit: $(git rev-parse --abbrev-ref HEAD)/$(git rev-parse HEAD)"
