#!/bin/bash

set -e

cd "${CODEBUILD_SRC_DIR}/demodjango"

echo -e "\nInstall dependencies"
poetry install

echo -e "\nFetch parameters from AWS Parameter Store"
USERNAME=$(aws ssm get-parameter --name "/copilot/demodjango/${TARGET_ENVIRONMENT}/secrets/BASIC_AUTH_USERNAME" --with-decryption --query "Parameter.Value" --output text)
PASSWORD=$(aws ssm get-parameter --name "/copilot/demodjango/${TARGET_ENVIRONMENT}/secrets/BASIC_AUTH_PASSWORD" --with-decryption --query "Parameter.Value" --output text)

export BASIC_AUTH_USERNAME="$USERNAME"
export BASIC_AUTH_PASSWORD="$PASSWORD"

echo -e "\nRun smoke tests"
./tests/browser/run.sh ${TARGET_ENVIRONMENT} smoke
