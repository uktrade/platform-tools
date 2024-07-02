#!/bin/bash

set -e

echo "Running maintenance page tests"

cd "${CODEBUILD_SRC_DIR}/demodjango-deploy"

# run offline for toolspr env

# curl / check that maintenance page returns default message and code
# TBC: Can we use the same tooling we've used for the smoke tests instead of curling etc.?

# curl with bypass header and check 200
# TBC: Should be able to set the header in and the rest basically be the regular smoke tests

# check env ip is whitelisted

# run online

# curl for 200 - Probably covered by the smoke tests below

echo -e "\nCheck we can view the page (running smoke tests)"
cd "${CODEBUILD_SRC_DIR}/demodjango"
./smoke_tests.sh ${TARGET_ENVIRONMENT}

