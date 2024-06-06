#!/bin/bash

# exit early if something goes wrong
set -e

# echo -e "\nBuild and install platform-helper"
# poetry build --no-interaction --format sdist --no-ansi
# pip install "dist/$(ls -t1 dist | head -1)"
# platform-helper --version

echo -e "\nGet CodeStar connection details"
codestarConnections=$(aws codestar-connections list-connections --provider-type GitHub --query "Connections[? ConnectionStatus == 'AVAILABLE']")
awsAccount=$(echo "$codestarConnections" | jq -r ".[0].OwnerAccountId")
codestarArn=$(echo "$codestarConnections" | jq -r ".[0].ConnectionArn")
codestarConnectionId=$(echo "${codestarArn##*/}")

echo -e "\nClone demodjango_deploy"
git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true
git clone "https://codestar-connections.eu-west-2.amazonaws.com/git-http/$awsAccount/eu-west-2/$codestarConnectionId/uktrade/demodjango-deploy.git"

echo -e "\ncd demodjango-deploy"
cd ./demodjango-deploy/

# Todo: Replace manually added PLATFORM_TOOLS_AWS_ACCOUNT_ID and PLATFORM_SANDBOX_AWS_ACCOUNT_ID environment variables

echo -e "\nConfigure platform-tools AWS Profile"
platformToolsAwsProfile="platform-tools"
aws configure --profile "$platformToolsAwsProfile" set account_id "$AWS_ACCOUNT_ID"
aws configure --profile "$platformToolsAwsProfile" set region "eu-west-2"
aws configure --profile "$platformToolsAwsProfile" set output "json"

echo -e "\nConfigure platform-sandbox AWS Profile"
platformSandboxAwsProfile="platform-sandbox"
aws configure --profile "$platformSandboxAwsProfile" set account_id "$PLATFORM_SANDBOX_AWS_ACCOUNT_ID"
aws configure --profile "$platformSandboxAwsProfile" set region "eu-west-2"
aws configure --profile "$platformSandboxAwsProfile" set output "json"

echo -e "\nAssume role to trigger environment pipeline"
assumedRole=$(aws sts assume-role \
    --role-arn "arn:aws:iam::$PLATFORM_SANDBOX_AWS_ACCOUNT_ID:role/regression-tests-assume-role-for-platform-tools" \
    --role-session-name "pull-request-regression-tests-$(date +%s)")
export AWS_ACCESS_KEY_ID=$(echo $assumedRole | jq -r .Credentials.AccessKeyId)
export AWS_SECRET_ACCESS_KEY=$(echo $assumedRole | jq -r .Credentials.SecretAccessKey)
export AWS_SESSION_TOKEN=$(echo $assumedRole | jq -r .Credentials.SessionToken)

# echo -e "\nRun platform-helper generate (which runs copilot make-addons & pipeline generate)"
# # The commands are run elsewhere in pipelines, but this gives us faster, more granular feedback
# PLATFORM_TOOLS_SKIP_VERSION_CHECK=true platform-helper generate

echo -e "\nStart deploy environment pipeline"
aws lambda invoke --function-name arn:aws:lambda:eu-west-2:$PLATFORM_SANDBOX_AWS_ACCOUNT_ID:function:start-toolspr-environment-pipeline --profile platform-sandbox response.json

# Todo: Wait for pipeline to complete, check status etc.

# echo -e "\nDeploy services"
# (ideally with pipeline)
# platform-helper codebase deploy --app demodjango --env toolspr --codebase application --commit <commit_hash>
# In the meantime, run the following from the demodjango-deploy codebase on your machine...
#   IMAGE_TAG=tag-latest copilot svc deploy --name celery-worker --env toolspr
#   IMAGE_TAG=tag-latest copilot svc deploy --name celery-beat --env toolspr
#   IMAGE_TAG=tag-latest copilot svc deploy --name web --env toolspr

# echo -e "\nRun smoke tests"
# From the demodjango codebase on your machine, run...
#   ./smoke_tests.sh toolspr
