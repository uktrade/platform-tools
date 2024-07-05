#!/bin/bash

set -e

echo "Running maintenance page tests"

echo -e "\nClone demodjango"
git clone "${GIT_CLONE_BASE_URL}/demodjango-deploy.git"

cd "${CODEBUILD_SRC_DIR}/demodjango-deploy" 
echo "Current demodjango-deploy branch/commit: $(git rev-parse --abbrev-ref HEAD)/$(git rev-parse HEAD)"

URL=https://internal.${TARGET_ENVIRONMENT}.demodjango.uktrade.digital/

echo -e "\nCheck we can view the page (running smoke tests)"
cd "${CODEBUILD_SRC_DIR}/demodjango"
./smoke_tests.sh ${TARGET_ENVIRONMENT} smoke

echo -e "\nRunning offline command"
OUTPUT=$(echo "y" | AWS_PROFILE=platform-sandbox PLATFORM_TOOLS_SKIP_VERSION_CHECK=true platform-helper environment offline --app demodjango --env "${TARGET_ENVIRONMENT}" --vpc platform-sandbox-dev)

echo "$OUTPUT"
MAINTENANCE_PAGE_BYPASS_VALUE=$(echo "$OUTPUT" | grep -oP 'Bypass-Key` header with value \K[^\s]+')

echo -e "\nCheck maintenance page is working and that we can view the site with Bypass-Key header"
cd "${CODEBUILD_SRC_DIR}/demodjango"
./smoke_tests.sh ${TARGET_ENVIRONMENT} maintenance_pages ${MAINTENANCE_PAGE_BYPASS_VALUE}

#TODO check env ip is whitelisted https://uktrade.atlassian.net/browse/DBTP-1161

echo -e "\nRunning online command"
AWS_PROFILE=platform-sandbox PLATFORM_TOOLS_SKIP_VERSION_CHECK=true platform-helper environment online --app demodjango --env ${TARGET_ENVIRONMENT}

echo -e "\nCheck we can view the page again (running smoke tests)"
cd "${CODEBUILD_SRC_DIR}/demodjango"
./smoke_tests.sh ${TARGET_ENVIRONMENT} smoke
