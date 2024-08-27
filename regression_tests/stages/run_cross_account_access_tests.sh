#!/bin/bash

set -e

echo -e "\nAssume cross account access role to access basic auth secrets"

DEMODJANGO_TOOLSPR_S3_CROSS_ACCOUNT_ROLE=""
DEMODJANGO_TOOLSPR_S3_BUCKET=""

assumed_role=$(aws sts assume-role \
    --role-arn "arn:aws:iam::$PLATFORM_SANDBOX_AWS_ACCOUNT_ID:role/$DEMODJANGO_TOOLSPR_S3_CROSS_ACCOUNT_ROLE" \
    --role-session-name "pull-request-regression-tests-x-account-s3-access-$(date +%s)")

PLATFORM_SANDBOX_AWS_ACCESS_KEY_ID=$(echo $assumed_role | jq -r .Credentials.AccessKeyId)
PLATFORM_SANDBOX_AWS_SECRET_ACCESS_KEY=$(echo $assumed_role | jq -r .Credentials.SecretAccessKey)
PLATFORM_SANDBOX_AWS_SESSION_TOKEN=$(echo $assumed_role | jq -r .Credentials.SessionToken)

export AWS_ACCESS_KEY_ID=$PLATFORM_SANDBOX_AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=$PLATFORM_SANDBOX_AWS_SECRET_ACCESS_KEY
export AWS_SESSION_TOKEN=$PLATFORM_SANDBOX_AWS_SESSION_TOKEN

echo -e "\nRead objects from bucket $DEMODJANGO_TOOLSPR_S3_BUCKET"

response=$(aws s3 list-objects-v2 \
    --bucket $DEMODJANGO_TOOLSPR_S3_BUCKET \
    --cli-connect-timeout 10 \
    --output json)

echo -e "Response: $response"