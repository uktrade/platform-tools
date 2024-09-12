#!/bin/bash

set -e

echo -e "\n\nClone demodjango_deploy\n"

git clone "${GIT_CLONE_BASE_URL}/demodjango-deploy.git"

cd "${CODEBUILD_SRC_DIR}/demodjango-deploy"
echo -e "\nCurrent demodjango-deploy branch/commit: $(git rev-parse --abbrev-ref HEAD)/$(git rev-parse HEAD)"
