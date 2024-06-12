#!/bin/bash

# exit early if something goes wrong
set -e

#./regression_tests/stages/build_platform_helper.sh

#./regression_tests/stages/clone_demodjango_deploy.sh

# Todo: Run platform-helper environment generate

#./regression_tests/stages/run_platform_helper_generate.sh

./regression_tests/stages/set_up_aws_config.sh

#./regression_tests/stages/run_environment_pipeline.sh

./regression_tests/stages/run_codebase_pipeline.sh

# echo -e "\nRun smoke tests"
# From the demodjango codebase on your machine, run...
#   ./smoke_tests.sh toolspr

# Slack alert if it fails on the main branch
