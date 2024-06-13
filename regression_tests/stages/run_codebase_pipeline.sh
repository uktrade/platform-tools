#!/bin/bash

set -e

source ./regression_tests/src/run_pipeline.sh

run_pipeline "Codebase" "pipeline-demodjango-application-toolspr" 1800
