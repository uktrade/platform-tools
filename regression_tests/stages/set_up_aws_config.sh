#!/bin/bash

set -e

cd "${CODEBUILD_SRC_DIR}"

echo -e "\nConfigure platform-sandbox AWS Profile"
profile_name="platform-sandbox"
# populates the ~/.aws/credentials file..
aws configure set aws_access_key_id "$PLATFORM_SANDBOX_AWS_ACCESS_KEY_ID" --profile "$profile_name"
aws configure set aws_secret_access_key "$PLATFORM_SANDBOX_AWS_SECRET_ACCESS_KEY" --profile "$profile_name"
aws configure set aws_session_token "$PLATFORM_SANDBOX_AWS_SESSION_TOKEN" --profile "$profile_name"
# populates the ~/.aws/config file..
aws configure set region "eu-west-2" --profile "$profile_name"
aws configure set output "json" --profile "$profile_name"
