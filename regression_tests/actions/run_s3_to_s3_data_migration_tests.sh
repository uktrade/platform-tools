#!/bin/bash

set -e

echo -e "\n\n### Run S3 to S3 data migration tests\n"

S3_MIGRATION_ROLE="demodjango-${TARGET_ENVIRONMENT}-shared-S3MigrationRole"
DESTINATION_BUCKET="demodjango-${TARGET_ENVIRONMENT}-shared"
SOURCE_BUCKET="s3-to-s3-data-migration-regression-test"
SOURCE_FILE="source_file.txt"

DESTINATION_FILE="copied_source_file_$(date +'%Y-%m-%d_%H-%M-%S').txt"

echo -e "\nAssume platform-sandbox role to access basic auth secrets"
# Todo: Look to extract to a helper script in a followup pull request
assumed_role=$(aws sts assume-role \
    --role-arn "arn:aws:iam::$PLATFORM_SANDBOX_AWS_ACCOUNT_ID:role/regression-tests-assume-role-for-platform-tools" \
    --role-session-name "pull-request-regression-tests-$(date +%s)")
PLATFORM_SANDBOX_AWS_ACCESS_KEY_ID=$(echo $assumed_role | jq -r .Credentials.AccessKeyId)
PLATFORM_SANDBOX_AWS_SECRET_ACCESS_KEY=$(echo $assumed_role | jq -r .Credentials.SecretAccessKey)
PLATFORM_SANDBOX_AWS_SESSION_TOKEN=$(echo $assumed_role | jq -r .Credentials.SessionToken)

export AWS_ACCESS_KEY_ID=$PLATFORM_SANDBOX_AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=$PLATFORM_SANDBOX_AWS_SECRET_ACCESS_KEY
export AWS_SESSION_TOKEN=$PLATFORM_SANDBOX_AWS_SESSION_TOKEN

echo -e "\nAssume platform sandbox S3MigrationRole to access basic auth secrets"
# Todo: Look to extract to a helper script in a followup pull request
assumed_role=$(aws sts assume-role \
    --role-arn "arn:aws:iam::$PLATFORM_SANDBOX_AWS_ACCOUNT_ID:role/$S3_MIGRATION_ROLE" \
    --role-session-name "pull-request-regression-tests-s3-to-s3-data-migration-$(date +%s)")

PLATFORM_SANDBOX_AWS_ACCESS_KEY_ID=$(echo $assumed_role | jq -r .Credentials.AccessKeyId)
PLATFORM_SANDBOX_AWS_SECRET_ACCESS_KEY=$(echo $assumed_role | jq -r .Credentials.SecretAccessKey)
PLATFORM_SANDBOX_AWS_SESSION_TOKEN=$(echo $assumed_role | jq -r .Credentials.SessionToken)

export AWS_ACCESS_KEY_ID=$PLATFORM_SANDBOX_AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=$PLATFORM_SANDBOX_AWS_SECRET_ACCESS_KEY
export AWS_SESSION_TOKEN=$PLATFORM_SANDBOX_AWS_SESSION_TOKEN

echo -e "\nCopy $SOURCE_FILE from $SOURCE_BUCKET to $DESTINATION_BUCKET"

response=$(aws s3 cp s3://$SOURCE_BUCKET/$SOURCE_FILE s3://$DESTINATION_BUCKET/$DESTINATION_FILE \
    --cli-connect-timeout 10 \
    --output json)

echo -e "Response: $response"
