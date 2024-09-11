#!/bin/bash

set -e

echo -e "\n\nRun codebase pipeline\n"

cd "${CODEBUILD_SRC_DIR}"

source ./regression_tests/src/run_pipeline.sh

# Todo: Come back to this...
# run_pipeline "Codebase" "pipeline-demodjango-application-${TARGET_ENVIRONMENT}" 1800
run_pipeline "Codebase" "pipeline-demodjango-application-dbtp-1291-regression-tests-temp" 1800
