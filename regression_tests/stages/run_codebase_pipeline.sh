#!/bin/bash

set -e

cd "${CODEBUILD_SRC_DIR}"

source ./regression_tests/src/run_pipeline.sh

run_pipeline "Codebase" "pipeline-demodjango-application-${targetEnvironment}" 1800
