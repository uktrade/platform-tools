#!/bin/bash

set -e

echo -e "\n\n### Clone demodjango\n"

git clone "${GIT_CLONE_BASE_URL}/demodjango.git"

cd "${CODEBUILD_SRC_DIR}/demodjango"
if [[ -n "${DEMODJANGO_BRANCH}" ]]; then
    echo -e "\nChecking out branch ${DEMODJANGO_BRANCH}\n"
    git checkout "${DEMODJANGO_BRANCH}"
fi

echo -e "\nCurrent demodjango branch/commit: $(git rev-parse --abbrev-ref HEAD)/$(git rev-parse HEAD)"
