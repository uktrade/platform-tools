#!/bin/bash

set -e

echo "Running maintenance page tests"

echo -e "\nClone demodjango"
git clone "${GIT_CLONE_BASE_URL}/demodjango-deploy.git"

cd "${CODEBUILD_SRC_DIR}/demodjango-deploy" 
echo "Current demodjango-deploy branch/commit: $(git rev-parse --abbrev-ref HEAD)/$(git rev-parse HEAD)"


URL=https://internal.${TARGET_ENVIRONMENT}.demodjango.uktrade.digital/

HTTP_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $URL)

if [ $HTTP_RESPONSE -eq 200 ]; then
    echo "The request was successful."
else
    echo "Expected 200 but received HTTP status code $HTTP_RESPONSE."
    exit 1

OUTPUT=$(AWS_PROFILE=platform-sandbox PLATFORM_TOOLS_SKIP_VERSION_CHECK=true platform-helper environment offline --app demodjango --env ${TARGET_ENVIRONMENT})

BYPASS_VALUE=$(echo "$OUTPUT" | grep -oP 'Bypass-Key` header with value \K[^\s]+')

HTTP_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $URL)

if [ $HTTP_RESPONSE -eq 503 ]; then
    echo "The request hit the maintenance page."
else
    echo "Expected 503 but received HTTP status code $HTTP_RESPONSE."
    exit 1

HTTP_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -H "Bypass-Key: $BYPASS_VALUE" $URL)

if [ $HTTP_RESPONSE -eq 200 ]; then
    echo "The request with Bypass-Key header was successful."
else
    echo "Expected 200 but received HTTP status code $HTTP_RESPONSE."
    exit 1

AWS_PROFILE=platform-sandbox PLATFORM_TOOLS_SKIP_VERSION_CHECK=true platform-helper environment online --app demodjango --env ${TARGET_ENVIRONMENT}

HTTP_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $URL)

if [ $HTTP_RESPONSE -eq 200 ]; then
    echo "The request was successful."
else
    echo "Expected 200 but received HTTP status code $HTTP_RESPONSE."
    exit 1


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

