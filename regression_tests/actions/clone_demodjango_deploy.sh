#!/bin/bash

set -e

echo -e "\n\n### Clone demodjango_deploy\n"

git clone "${GIT_CLONE_BASE_URL}/demodjango-deploy.git"

cd "${CODEBUILD_SRC_DIR}/demodjango-deploy"
if [[ -n "${DEMODJANGO_DEPLOY_BRANCH}" ]]; then
    echo -e "\nChecking out branch ${DEMODJANGO_DEPLOY_BRANCH}\n"
    git checkout "${DEMODJANGO_DEPLOY_BRANCH}"
fi
echo -e "\nCurrent demodjango-deploy branch/commit: $(git rev-parse --abbrev-ref HEAD)/$(git rev-parse HEAD)"
