#!/bin/bash

# exit early if something goes wrong
set -e

# Todo: Re-enable this...
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

# Todo: Replace manually added TEST_PLATFORM_TOOLS_AWS_ACCOUNT_ID and PLATFORM_SANDBOX_AWS_ACCOUNT_ID environment variables

# Todo: extract a method to create these profiles
# echo -e "\nConfigure platform-tools AWS Profile"
# platformToolsAwsProfile="platform-tools"
# aws configure --profile "$platformToolsAwsProfile" set account_id "$AWS_ACCOUNT_ID"
# aws configure --profile "$platformToolsAwsProfile" set region "eu-west-2"
# aws configure --profile "$platformToolsAwsProfile" set output "json"

# echo -e "\nConfigure platform-sandbox AWS Profile"
# platformSandboxAwsProfile="platform-sandbox"
# aws configure --profile "$platformSandboxAwsProfile" set account_id "$PLATFORM_SANDBOX_AWS_ACCOUNT_ID"
# aws configure --profile "$platformSandboxAwsProfile" set region "eu-west-2"
# aws configure --profile "$platformSandboxAwsProfile" set output "json"

# platformSandboxAwsProfile="platform-sandbox"
# # Configure AWS CLI profile
# echo -e "\nConfigure $AWS_PROFILE AWS Profile"
# # populates the ~/.aws/credentials file
# aws configure set aws_access_key_id "$ACCESS_KEY_ID" --profile "$AWS_PROFILE"
# aws configure set aws_secret_access_key "$SECRET_ACCESS_KEY" --profile "$AWS_PROFILE"
# # populates the ~/.aws/config file & platform-sandbox profile
# aws configure set region "eu-west-2" --profile "$AWS_PROFILE"
# aws configure set output "json" --profile "$AWS_PROFILE"

# Function to configure an AWS profile
configure_aws_profile() {
  local profile_name=$1
  local access_key_id=$2
  local secret_access_key=$2

  echo -e "\nConfigure $profile_name AWS Profile"
  # populates the ~/.aws/credentials file
  aws configure set aws_access_key_id "$access_key_id" --profile "$profile_name"
  aws configure set aws_secret_access_key "$secret_access_key" --profile "$profile_name"
  
  # Doesn't look like account_id is a valid option to configure
  # aws configure set account_id "$account_id" --profile "$profile_name"
  
  # populates the ~/.aws/config file & platform-sandbox profile
  aws configure set region "eu-west-2" --profile "$profile_name"
  aws configure set output "json" --profile "$profile_name"
}

#----------------------------------------------
platform_tools_caller=(aws sts get-caller-identity)
echo "$platform_tools_caller"

export TEST_PLATFORM_TOOLS_AWS_ACCOUNT_ID=$(echo "$platform_tools_caller" | jq -r .Account)
echo "TEST_PLATFORM_TOOLS_AWS_ACCOUNT_ID: $TEST_PLATFORM_TOOLS_AWS_ACCOUNT_ID"

echo -e "\nAssume platform-tools role to trigger environment pipeline"
temp_role=$(aws sts assume-role \
    --role-arn "arn:aws:iam::$TEST_PLATFORM_TOOLS_AWS_ACCOUNT_ID:role/codebuild-platform-tools-test-service-role" \
    --role-session-name "codebuild-pull-request-regression-tests-$(date +%s)")
echo "$temp_role"

export PLATFORM_TOOLS_AWS_ACCESS_KEY_ID=$(echo $temp_role | jq -r .Credentials.AccessKeyId)
export PLATFORM_TOOLS_AWS_SECRET_ACCESS_KEY=$(echo $temp_role | jq -r .Credentials.SecretAccessKey)


# Configure platform-tools profile
configure_aws_profile "platform-tools" "$TEST_PLATFORM_TOOLS_AWS_ACCOUNT_ID" "$PLATFORM_TOOLS_AWS_ACCESS_KEY_ID" "$PLATFORM_TOOLS_AWS_ACCESS_KEY_ID"

#------------------------------------------------

echo -e "\nAssume platform-sandbox role to trigger environment pipeline"
temp_role=$(aws sts assume-role \
    --role-arn "arn:aws:iam::$PLATFORM_SANDBOX_AWS_ACCOUNT_ID:role/regression-tests-assume-role-for-platform-tools" \
    --role-session-name "pull-request-regression-tests-$(date +%s)")
echo "$temp_role"

export PLATFORM_SANDBOX_AWS_ACCESS_KEY_ID=$(echo $temp_role | jq -r .Credentials.AccessKeyId)
export PLATFORM_SANDBOX_AWS_SECRET_ACCESS_KEY=$(echo $temp_role | jq -r .Credentials.SecretAccessKey)

# Configure platform-sandbox profile
configure_aws_profile "platform-sandbox" "$PLATFORM_SANDBOX_AWS_ACCESS_KEY_ID" "$PLATFORM_SANDBOX_AWS_SECRET_ACCESS_KEY"
#------------------------------------------------

aws sts get-caller-identity

echo -e "\nRun deploy environment pipeline"
aws codepipeline start-pipeline-execution --name demodjango-environment-pipeline-TOOLSPR --profile platform-sandbox

# export AWS_SESSION_TOKEN=$(echo $temp_role | jq -r .Credentials.SessionToken)
# export AWS_DEFAULT_PROFILE=platform-sandbox
# export AWS_PROFILE=platform-sandbox

# Todo: Re-enable this...
# echo -e "\nRun platform-helper generate (which runs copilot make-addons & pipeline generate)"
# # The commands are run elsewhere in pipelines, but this gives us faster, more granular feedback
# PLATFORM_TOOLS_SKIP_VERSION_CHECK=true platform-helper generate

# Todo: Decide where the Terraform for the things we need in the platform-sandbox account should live
# -------------------------------------------------------------------------------------------------------
# Todo: Terraform IAM stuff
#In platform-sandbox.... (Added to terraform tools/env/prod/iam.tf)
#
#    regression-tests-assume-role-for-platform-tools
#
#        Trust policy...
#        {
#            "Version": "2012-10-17",
#            "Statement": [
#                {
#                    "Effect": "Allow",
#                    "Principal": {
#                        "AWS": "arn:aws:iam::<platform_tools_account_id>:role/codebuild-platform-tools-test-service-role"
#                    },
#                    "Action": "sts:AssumeRole",
#                    "Condition": {}
#                }
#            ]
#        }
#
#        Permission policy...
#        {
#            "Version": "2012-10-17",
#            "Statement": [
#                {
#                    "Sid": "allow-start-toolspr-environment-pipeline",
#                    "Effect": "Allow",
#                    "Action": "lambda:InvokeFunction",
#                    "Resource": "arn:aws:lambda:eu-west-2:<platform_sandbox_account_id>:function:start-toolspr-environment-pipeline"
#                }
#            ]
#        }
#
# -------------------------------------------------------------------------------------------------------
#In platform-tools... (Added to terraform-tools/env/prod/iam.tf)
#
#    codebuild-platform-tools-test-service-role > regression-tests (policy)
#
      #  {
      #      "Version": "2012-10-17",
      #      "Statement": [
      #          {
      #              "Sid": "TBC",
      #              "Effect": "Allow",
      #              "Action": "lambda:InvokeFunction",
      #              "Resource": "arn:aws:lambda:eu-west-2:<platform_sandbox_account_id>:function:start-toolspr-environment-pipeline"
      #          },
      #          {
      #              "Sid": "TBC",
      #              "Effect": "Allow",
      #              "Action": "sts:AssumeRole",
      #              "Resource": "arn:aws:iam::<platform_sandbox_account_id>:role/regression-tests-assume-role-for-platform-tools"
      #          }
      #      ]
      #  }

# -------------------------------------------------------------------------------------------------------
# Todo: Terraform the Lambda function (Added to terraform-tools/env/prod/lambda.tf)
#In platform-sandbox...
#
#    Python 3.12
#
#    import json
#    import boto3
#
#    def lambda_handler(event, context):
#        client = boto3.client('codepipeline')
#
#        response = client.start_pipeline_execution(
#            name='demodjango-environment-pipeline-TOOLSPR'
#        )
#
#        return {
#            'statusCode': response.get("ResponseMetadata").get("HTTPStatusCode"),
#            'body': response
#        }
#
#    Needs to allows access to the things from the other account, speak to JOhn, https://docs.aws.amazon.com/lambda/latest/dg/access-control-resource-based.html#permissions-resource-xaccountinvoke
#
#    It's policy will need to be allowed to start the pipeline...
#
#    {
#        "Version": "2012-10-17",
#        "Statement": [
#            {
#                "Sid": "VisualEditor0",
#                "Effect": "Allow",
#                "Action": "codepipeline:StartPipelineExecution",
#                "Resource": "arn:aws:codepipeline:eu-west-2:<platform_sandbox_account_id>:demodjango-environment-pipeline-TOOLSPR"
#            }
#        ]
#    }

#     Resource based policy

      # {
      #   "Version": "2012-10-17",
      #   "Id": "default",
      #   "Statement": [
      #     {
      #       "Sid": "AllowInvokeFunction",
      #       "Effect": "Allow",
      #       "Principal": {
      #         "AWS": "arn:aws:iam::<platform_tools_account_id>:role/codebuild-platform-tools-test-service-role"
      #       },
      #       "Action": "lambda:InvokeFunction",
      #       "Resource": "arn:aws:lambda:eu-west-2:<platform_sandbox_account_id>:function:start-toolspr-environment-pipeline"
      #     }
      #   ]
      # }
# -------------------------------------------------------------------------------------------------------
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
