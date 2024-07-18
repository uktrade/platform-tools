#!/bin/bash

set -e

cd "${CODEBUILD_SRC_DIR}/demodjango"

echo "y" | AWS_PROFILE=platform-sandbox PLATFORM_TOOLS_SKIP_VERSION_CHECK=true platform-helper environment online --app demodjango --env ${TARGET_ENVIRONMENT} || true
