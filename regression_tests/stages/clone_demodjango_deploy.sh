#!/bin/bash

set -e

echo -e "\nClone demodjango_deploy"

git clone "https://codestar-connections.eu-west-2.amazonaws.com/git-http/$aws_account/eu-west-2/$codestar_connection_id/uktrade/demodjango-deploy.git"

cd "${CODEBUILD_SRC_DIR}/demodjango-deploy"
echo "Current demodjango-deploy branch/commit: $(git rev-parse --abbrev-ref HEAD)/$(git rev-parse HEAD)"

