#!/bin/bash

# exit early if something goes wrong
set -e

echo -e "\nBuild and install platform-helper"
poetry build --no-interaction --format sdist --no-ansi
pip install "dist/$(ls -t1 dist | head -1)"
platform-helper --version

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

echo -e "\nConfigure AWS Profile"
export AWS_PROFILE="platform-tools"
aws configure --profile "$AWS_PROFILE" set account_id "$AWS_ACCOUNT_ID"
aws configure --profile "$AWS_PROFILE" set region "eu-west-2"
aws configure --profile "$AWS_PROFILE" set output "json"

# echo -e "\nRun deploy environment pipeline"
# Command TBC, but we should trigger a demodjango-toolspr-environment-pipeline
# Todo: Create demodjango-toolspr-environment-pipeline
# In the meantime, run the following from the demodjango-deploy codebase on your machine...
#   cd terraform/environments/toolspr
#   terraform init -upgrade
#   terraform apply
#   cd ../../../
#   platform-helper environment generate --name toolspr --vpc-name platform-sandbox-dev
#   copilot env init --name toolspr --profile $AWS_PROFILE --default-config
#   copilot env deploy --name toolspr

echo -e "\nRun platform-helper generate (which runs copilot make-addons & pipeline generate)"
PLATFORM_TOOLS_SKIP_VERSION_CHECK=true platform-helper generate

# echo -e "\nDeploy codebase pipeline"
# Run the following from the demodjango-deploy codebase on your machine...
#   copilot pipeline deploy

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
