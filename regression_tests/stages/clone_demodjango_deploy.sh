#!/bin/bash

set -e

echo -e "\nClone demodjango_deploy"

git clone "${GIT_CLONE_BASE_URL}/demodjango-deploy.git"

git checkout DBTP-1096-environment-vpc-default-bug

cd "${CODEBUILD_SRC_DIR}/demodjango-deploy"
echo "Current demodjango-deploy branch/commit: $(git rev-parse --abbrev-ref HEAD)/$(git rev-parse HEAD)"
