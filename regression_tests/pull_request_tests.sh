#!/bin/bash

# exit early if something goes wrong
set -e

echo -e "\nBuild and install platform-helper"
poetry build --no-interaction --format sdist --no-ansi
pip install "dist/$(ls -t1 dist | head -1)"
platform-helper --version

echo -e "\nGet CodeStar connection details"
codestar_connections=$(aws codestar-connections list-connections --provider-type GitHub --query "Connections[? ConnectionStatus == 'AVAILABLE']")
aws_account=$(echo "$codestar_connections" | jq -r ".[0].OwnerAccountId")
codestar_arn=$(echo "$codestar_connections" | jq -r ".[0].ConnectionArn")
codestar_connection_id=$(echo "${codestar_arn##*/}")

echo -e "\nClone demodjango_deploy"
git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true
git clone "https://codestar-connections.eu-west-2.amazonaws.com/git-http/$aws_account/eu-west-2/$codestar_connection_id/uktrade/demodjango-deploy.git"

echo -e "\ncd demodjango-deploy"
cd ./demodjango-deploy/

echo -e "\nRun platform-helper generate (which runs copilot make-addons & pipeline generate)"
# The commands are run elsewhere in pipelines, but this gives us faster, more granular feedback
PLATFORM_TOOLS_SKIP_VERSION_CHECK=true platform-helper generate

echo -e "\nAssume platform-sandbox role to trigger environment pipeline"
assumed_role=$(aws sts assume-role \
    --role-arn "arn:aws:iam::$PLATFORM_SANDBOX_AWS_ACCOUNT_ID:role/regression-tests-assume-role-for-platform-tools" \
    --role-session-name "pull-request-regression-tests-$(date +%s)")
PLATFORM_SANDBOX_AWS_ACCESS_KEY_ID=$(echo $assumed_role | jq -r .Credentials.AccessKeyId)
PLATFORM_SANDBOX_AWS_SECRET_ACCESS_KEY=$(echo $assumed_role | jq -r .Credentials.SecretAccessKey)
PLATFORM_SANDBOX_AWS_SESSION_TOKEN=$(echo $assumed_role | jq -r .Credentials.SessionToken)

cd ..
./regression_tests/stages/set_up_aws_config.sh
./regression_tests/stages/run_environment_pipeline.sh

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
