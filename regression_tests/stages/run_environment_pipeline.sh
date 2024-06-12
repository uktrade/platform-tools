#!/bin/bash

set -e

source ./regression_tests/src/run_pipeline.sh

run_pipeline "Environment" "demodjango-environment-pipeline-TOOLSPR"
