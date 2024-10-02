#!/bin/bash

set -e

echo -e "\n\n### Run demodjango smoke tests for ${TARGET_ENVIRONMENT} environment"

cd "${CODEBUILD_SRC_DIR}/demodjango"

echo -e "\nAssume platform-sandbox role to access basic auth secrets"
# Todo: Look to extract to a helper script in a followup pull request
assumed_role=$(aws sts assume-role \
    --role-arn "arn:aws:iam::$PLATFORM_SANDBOX_AWS_ACCOUNT_ID:role/platform-regression-tests-role" \
    --role-session-name "pull-request-regression-tests-$(date +%s)")
PLATFORM_SANDBOX_AWS_ACCESS_KEY_ID=$(echo $assumed_role | jq -r .Credentials.AccessKeyId)
PLATFORM_SANDBOX_AWS_SECRET_ACCESS_KEY=$(echo $assumed_role | jq -r .Credentials.SecretAccessKey)
PLATFORM_SANDBOX_AWS_SESSION_TOKEN=$(echo $assumed_role | jq -r .Credentials.SessionToken)

export AWS_ACCESS_KEY_ID=$PLATFORM_SANDBOX_AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=$PLATFORM_SANDBOX_AWS_SECRET_ACCESS_KEY
export AWS_SESSION_TOKEN=$PLATFORM_SANDBOX_AWS_SESSION_TOKEN

echo -e "\nFetch parameters from AWS Parameter Store"
USERNAME=$(aws ssm get-parameter --name "/copilot/demodjango/${TARGET_ENVIRONMENT}/secrets/BASIC_AUTH_USERNAME" --with-decryption --query "Parameter.Value" --output text)
PASSWORD=$(aws ssm get-parameter --name "/copilot/demodjango/${TARGET_ENVIRONMENT}/secrets/BASIC_AUTH_PASSWORD" --with-decryption --query "Parameter.Value" --output text)

export BASIC_AUTH_USERNAME="$USERNAME"
export BASIC_AUTH_PASSWORD="$PASSWORD"

echo -e "\nRun smoke tests"
./tests/browser/run.sh ${TARGET_ENVIRONMENT} smoke

cd "${CODEBUILD_SRC_DIR}"
