#!/bin/bash

set -e

echo -e "\n\nRun environment pipeline\n"

cd "${CODEBUILD_SRC_DIR}"

source ./regression_tests/src/run_pipeline.sh

run_pipeline "Environment" "demodjango-${TARGET_ENVIRONMENT}-environment-pipeline" 660
