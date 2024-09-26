#!/bin/bash

set -e

echo -e "\n\n### Assume platform-sandbox role to trigger environment pipeline\n"

cd "${CODEBUILD_SRC_DIR}"

assumed_role=$(aws sts assume-role \
    --role-arn "arn:aws:iam::$PLATFORM_SANDBOX_AWS_ACCOUNT_ID:role/regression-tests-assume-role-for-platform-tools" \
    --role-session-name "pull-request-regression-tests-$(date +%s)")
PLATFORM_SANDBOX_AWS_ACCESS_KEY_ID=$(echo $assumed_role | jq -r .Credentials.AccessKeyId)
PLATFORM_SANDBOX_AWS_SECRET_ACCESS_KEY=$(echo $assumed_role | jq -r .Credentials.SecretAccessKey)
PLATFORM_SANDBOX_AWS_SESSION_TOKEN=$(echo $assumed_role | jq -r .Credentials.SessionToken)

echo -e "\n\nConfigure platform-sandbox AWS Profile\n"

profile_name="platform-sandbox"
# populates the ~/.aws/credentials file..
aws configure set aws_access_key_id "$PLATFORM_SANDBOX_AWS_ACCESS_KEY_ID" --profile "$profile_name"
aws configure set aws_secret_access_key "$PLATFORM_SANDBOX_AWS_SECRET_ACCESS_KEY" --profile "$profile_name"
aws configure set aws_session_token "$PLATFORM_SANDBOX_AWS_SESSION_TOKEN" --profile "$profile_name"
# populates the ~/.aws/config file..
aws configure set region "eu-west-2" --profile "$profile_name"
aws configure set output "json" --profile "$profile_name"
