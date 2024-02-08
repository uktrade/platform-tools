#!/bin/bash

# exit early if something goes wrong
set -e

#echo "Build and install copilot-helper"
#poetry build --no-interaction --format sdist --no-ansi
#pip install "dist/$(ls -t1 dist | head -1)"
#copilot-helper --version

echo "Get CodeStar connection details"
# todo: break this up to get account ID and ARM
codestarConnections=$(aws codestar-connections list-connections --provider-type GitHub --query "Connections[? ConnectionStatus == 'AVAILABLE']")
awsAccount=$(echo "$codestarConnections" | jq -r ".[0].OwnerAccountId")
codestarArn=$(echo "$codestarConnections" | jq -r ".[0].ConnectionArn")
codestarConnectionId=$(echo "${codestarArn##*/}")

echo "Clone demodjango_deploy"
git clone "https://codestar-connections.eu-west-2.amazonaws.com/git-http/$awsAccount/" \
    "eu-west-2/$codestarConnectionId/uktrade/demodjango-deploy.git"
