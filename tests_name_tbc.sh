#!/bin/bash

# exit early if something goes wrong
set -e

# Todo: Make this do something...
export COPILOT_HELPER_DISABLE_VERSION_CHECK="true"

echo -e "\nBuild and install copilot-helper"
poetry build --no-interaction --format sdist --no-ansi
pip install "dist/$(ls -t1 dist | head -1)"
copilot-helper --version

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

echo -e "\nRun make-addons from copilot-helper"
export AWS_PROFILE="platform-tools"
aws configure --profile "$AWS_PROFILE" set account_id "$PLATFORM_TOOLS_ACCOUNT_ID"
aws configure --profile "$AWS_PROFILE" set region "eu-west-2"
aws configure --profile "$AWS_PROFILE" set output "json"
copilot-helper copilot make-addons
ls ./copilot/environments/addons

echo -e "\nAssume demodjango-executionrole"
aws sts assume-role \
    --role-arn "arn:aws:iam::$PLATFORM_TOOLS_ACCOUNT_ID:role/demodjango-executionrole" \
    --role-session-name "copilot-tools-regression-pipeline-$CODEBUILD_BUILD_NUMBER"

echo -e "\nRun copilot env init"
copilot env init --name toolspr --profile $AWS_PROFILE --default-config

# deploy env

# deploy services

# run smoke tests
