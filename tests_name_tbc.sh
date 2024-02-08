#!/bin/bash

# exit early if something goes wrong
set -e

echo "Build and install copilot-helper"
poetry build --no-interaction --format sdist --no-ansi
pip install "dist/$(ls -t1 dist | head -1)"
copilot-helper --version

echo "Get CodeStar connection details"
# todo: break this up to get account ID and ARM
codestarArn=$(aws codestar-connections list-connections --provider-type GitHub --query "Connections[? ConnectionStatus == 'AVAILABLE']" | jq -r ".[0].ConnectionArn")
codestarArn=$(aws codestar-connections list-connections --provider-type GitHub --query "Connections[? ConnectionStatus == 'AVAILABLE']" | jq -r ".[0].ConnectionArn")
echo "$codestarArn"

codestarArnFromAccount=$(echo "${codestarArn#*arn:aws:codestar-connections:eu-west-2:}")
echo "$codestarArnFromAccount"

codestarId=$("${codestarArnFromAccount#*/}")
echo "$codestarId"

echo "Clone demodjango_deploy"
#git clone "https://codestar-connections.eu-west-2.amazonaws.com/git-http/AWS ACCOUNT/" \
#        "eu-west-2/CSID/uktrade/demodjango-deploy.git"
