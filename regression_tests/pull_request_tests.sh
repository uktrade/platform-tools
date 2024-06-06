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

# Todo: Replace manually added PLATFORM_TOOLS_AWS_ACCOUNT_ID and PLATFORM_SANDBOX_AWS_ACCOUNT_ID environment variables

# Todo: extract a method to create these profiles
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

# Todo: Re-enable this...
# echo -e "\nRun platform-helper generate (which runs copilot make-addons & pipeline generate)"
# # The commands are run elsewhere in pipelines, but this gives us faster, more granular feedback
# PLATFORM_TOOLS_SKIP_VERSION_CHECK=true platform-helper generate

# Todo: Decide where the Terraform for the things we need in the platform-sandbox account should live

# Todo: Terraform IAM stuff
#In platform-sandbox....
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
#In platform-tools...
#
#    codebuild-platform-tools-test-service-role > regression-tests (policy)
#
#        {
#            "Version": "2012-10-17",
#            "Statement": [
#                {
#                    "Sid": "TBC",
#                    "Effect": "Allow",
#                    "Action": "lambda:InvokeFunction",
#                    "Resource": "arn:aws:lambda:eu-west-2:<platform_sandbox_account_id>:function:start-toolspr-environment-pipeline"
#                },
#                {
#                    "Sid": "TBC",
#                    "Effect": "Allow",
#                    "Action": "sts:AssumeRole",
#                    "Resource": "arn:aws:iam::<platform_sandbox_account_id>:role/regression-tests-assume-role-for-platform-tools"
#                }
#            ]
#        }

# Todo: Terraform the Lambda function
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
