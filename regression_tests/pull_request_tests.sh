#!/bin/bash

configure_aws_profile() {
  local profile_name=$1
  local access_key_id=$2
  local secret_access_key=$3
  local session_token_key=$4

  echo -e "\nConfigure $profile_name AWS Profile"
  # populates the ~/.aws/credentials file
  aws configure set aws_access_key_id "$access_key_id" --profile "$profile_name"
  aws configure set aws_secret_access_key "$secret_access_key" --profile "$profile_name"
  aws configure set aws_session_token "$session_token_key" --profile "$profile_name"

  # populates the ~/.aws/config file
  aws configure set region "eu-west-2" --profile "$profile_name"
  aws configure set output "json" --profile "$profile_name"
}

# exit early if something goes wrong
set -e

# Todo: Re-enable this...
# echo -e "\nBuild and install platform-helper"
# poetry build --no-interaction --format sdist --no-ansi
# pip install "dist/$(ls -t1 dist | head -1)"
# platform-helper --version

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

# Todo: Re-enable this...
# echo -e "\nRun platform-helper generate (which runs copilot make-addons & pipeline generate)"
# # The commands are run elsewhere in pipelines, but this gives us faster, more granular feedback
# PLATFORM_TOOLS_SKIP_VERSION_CHECK=true platform-helper generate
#----------------------------------------------

echo -e "\nAssume platform-sandbox role to trigger environment pipeline"
assumed_role=$(aws sts assume-role \
    --role-arn "arn:aws:iam::$PLATFORM_SANDBOX_AWS_ACCOUNT_ID:role/regression-tests-assume-role-for-platform-tools" \
    --role-session-name "pull-request-regression-tests-$(date +%s)")
PLATFORM_SANDBOX_AWS_ACCESS_KEY_ID=$(echo $assumed_role | jq -r .Credentials.AccessKeyId)
PLATFORM_SANDBOX_AWS_SECRET_ACCESS_KEY=$(echo $assumed_role | jq -r .Credentials.SecretAccessKey)
PLATFORM_SANDBOX_AWS_SESSION_TOKEN=$(echo $assumed_role | jq -r .Credentials.SessionToken)

echo -e "\nConfigure platform-sandbox profile"
configure_aws_profile "platform-sandbox" "$PLATFORM_SANDBOX_AWS_ACCESS_KEY_ID" "$PLATFORM_SANDBOX_AWS_SECRET_ACCESS_KEY" "$PLATFORM_SANDBOX_AWS_SESSION_TOKEN"

echo -e "\nRun deploy environment pipeline"
aws codepipeline start-pipeline-execution --name demodjango-environment-pipeline-TOOLSPR --profile platform-sandbox

# Todo: Wait for pipeline to complete, check status etc.
count=0

while  count -le 10 ;
do
   count=$((count+1))
   echo $count
done 

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
