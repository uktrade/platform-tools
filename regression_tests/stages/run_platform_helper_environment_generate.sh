#!/bin/bash 

set -e

cd "${CODEBUILD_SRC_DIR}/demodjango-deploy"

echo -e "\nRun platform-helper environment generate"
# The command is run elsewhere in pipelines, but this gives us faster, more granular feedback
AWS_PROFILE=platform-sandbox PLATFORM_TOOLS_SKIP_VERSION_CHECK=true platform-helper environment generate --name ${TARGET_ENVIRONMENT}
