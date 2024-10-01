#!/bin/bash

set -e

echo -e "\n\n### Run codebase pipeline for ${TARGET_ENVIRONMENT} environment\n"

cd "${CODEBUILD_SRC_DIR}"

source ./regression_tests/src/run_pipeline.sh

run_pipeline "Codebase" "pipeline-demodjango-application-${TARGET_ENVIRONMENT}" 3600
