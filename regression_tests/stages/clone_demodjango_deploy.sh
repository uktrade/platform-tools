#!/bin/bash

echo -e "\nGet CodeStar connection details"
codestar_connections=$(aws codestar-connections list-connections --provider-type GitHub --query "Connections[? ConnectionStatus == 'AVAILABLE']")
aws_account=$(echo "$codestar_connections" | jq -r ".[0].OwnerAccountId")
codestar_arn=$(echo "$codestar_connections" | jq -r ".[0].ConnectionArn")
codestar_connection_id=$(echo "${codestar_arn##*/}")

echo -e "\nClone demodjango_deploy"
git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true
git clone "https://codestar-connections.eu-west-2.amazonaws.com/git-http/$aws_account/eu-west-2/$codestar_connection_id/uktrade/demodjango-deploy.git"
