#!/bin/bash

# exit early if something goes wrong
set -e

echo -e "\nCurrent platform-tools branch/commit: $(git rev-parse --abbrev-ref HEAD)/$(git rev-parse HEAD)"

source ./regression_tests/stages/set_up_git_config.sh
echo "Base url: $GIT_CLONE_BASE_URL"
# ./regression_tests/stages/set_up_aws_config.sh

# ./regression_tests/stages/build_platform_helper.sh

# ./regression_tests/stages/clone_demodjango_deploy.sh

# ./regression_tests/stages/run_platform_helper_environment_generate.sh

# ./regression_tests/stages/run_platform_helper_generate.sh

# Todo: Run copilot pipeline deploy

# ./regression_tests/stages/run_environment_pipeline.sh

# ./regression_tests/stages/run_codebase_pipeline.sh

# Todo: echo -e "\nRun smoke tests"
# From the demodjango codebase on your machine, run...
#   ./smoke_tests.sh toolspr

echo -e "\nCommand to run smoke tests from pull_request_tests.sh"
./regression_tests/stages/run_demodjango_smoke_tests.sh

# Todo: Slack alert if it fails on the main branch

# Todo: Prevent multiple triggerings resulting in overlapping test runs

# Todo: Update trigger to run it from all four codebases on merge to main
