#!/bin/bash

set -e

echo -e "\n\n### Run codebase pipeline\n"

cd "${CODEBUILD_SRC_DIR}"

source ./regression_tests/src/run_pipeline.sh

run_pipeline "Codebase" "pipeline-demodjango-application-${TARGET_ENVIRONMENT}" 1800
