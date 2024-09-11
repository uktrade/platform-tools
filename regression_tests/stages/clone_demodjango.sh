#!/bin/bash

set -e

echo -e "\n\nClone demodjango\n"

git clone "${GIT_CLONE_BASE_URL}/demodjango.git"
if [[ -z "${DEMODJANGO_BRANCH}" ]]; then
    git checkout "${DEMODJANGO_BRANCH}"
fi

cd "${CODEBUILD_SRC_DIR}/demodjango"
echo -e "\nCurrent demodjango branch/commit: $(git rev-parse --abbrev-ref HEAD)/$(git rev-parse HEAD)"
