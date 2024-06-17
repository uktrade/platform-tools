#!/bin/bash

set -e

echo -e "\nGet CodeStar connection details"
codestar_connections=$(aws codestar-connections list-connections --provider-type GitHub --query "Connections[? ConnectionStatus == 'AVAILABLE']")
aws_account=$(echo "$codestar_connections" | jq -r ".[0].OwnerAccountId")
codestar_arn=$(echo "$codestar_connections" | jq -r ".[0].ConnectionArn")
codestar_connection_id=$(echo "${codestar_arn##*/}")

export GIT_CLONE_BASE_URL="https://codestar-connections.eu-west-2.amazonaws.com/git-http/$aws_account/eu-west-2/$codestar_connection_id/uktrade"

git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true
