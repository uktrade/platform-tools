#!/bin/bash

# exit early if something goes wrong
set -e

export TARGET_ENVIRONMENT=${TARGET_ENVIRONMENT:-toolspr}

echo -e "\nCurrent platform-tools branch/commit: $(git rev-parse --abbrev-ref HEAD)/$(git rev-parse HEAD)"

source ./regression_tests/stages/set_up_git_config.sh

./regression_tests/stages/set_up_aws_config.sh

./regression_tests/stages/build_platform_helper.sh

./regression_tests/stages/clone_demodjango_deploy.sh

./regression_tests/stages/run_platform_helper_environment_generate.sh

./regression_tests/stages/run_platform_helper_generate.sh

# Todo: DBTP-1073 Include deploying environment pipelines in regression tests

# Todo: DBTP-1074 Include deploying codebase pipelines in regression tests

# ./regression_tests/stages/run_environment_pipeline.sh

# ./regression_tests/stages/run_codebase_pipeline.sh

./regression_tests/stages/run_demodjango_smoke_tests.sh

./regression_tests/stages/run_maintenance_page_tests.sh

# Todo: DBTP-1076 Ensure regression tests builds run one at a time

# Todo: DBTP-1075 Trigger regression tests off all four main DBT Platform Codebases
