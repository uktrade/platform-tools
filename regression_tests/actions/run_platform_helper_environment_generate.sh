#!/bin/bash

set -e

echo -e "\n\n### Run platform-helper environment generate\n"

cd "${CODEBUILD_SRC_DIR}/demodjango-deploy"

# The command is run elsewhere in pipelines, but this gives us faster, more granular feedback
AWS_PROFILE=platform-sandbox PLATFORM_TOOLS_SKIP_VERSION_CHECK=true platform-helper environment generate --name ${TARGET_ENVIRONMENT}
