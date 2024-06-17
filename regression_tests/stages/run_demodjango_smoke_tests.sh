#!/bin/bash 

set -e

echo -e "\nClone demodjango"
git clone "https://codestar-connections.eu-west-2.amazonaws.com/git-http/$aws_account/eu-west-2/$codestar_connection_id/uktrade/demodjango.git"

cd "${CODEBUILD_SRC_DIR}/demodjango" 
echo "Current demodjango branch/commit: $(git rev-parse --abbrev-ref HEAD)/$(git rev-parse HEAD)"

echo -e "\nInstall dependencies"
poetry install

echo -e "\nRun smoke tests"
./smoke_tests.sh toolspr