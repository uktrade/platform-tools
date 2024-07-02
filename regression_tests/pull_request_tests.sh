#!/bin/bash

# exit early if something goes wrong
set -e

# Todo: Temporary hacks, remove this block to run it in CodeBuild
export GIT_CLONE_BASE_URL="git@github.com:uktrade"
export CODEBUILD_SRC_DIR="$(pwd)"

export TARGET_ENVIRONMENT=${TARGET_ENVIRONMENT:-toolspr}

echo -e "\nCurrent platform-tools branch/commit: $(git rev-parse --abbrev-ref HEAD)/$(git rev-parse HEAD)"

# Todo: Uncomment before merge or to run in CodeBuild
# source ./regression_tests/stages/set_up_git_config.sh

# Todo: Uncomment before merge or to run in CodeBuild
# ./regression_tests/stages/assume_platform_sandbox_role.sh

# Todo: Uncomment before merge or to run in CodeBuild
# ./regression_tests/stages/set_up_aws_config.sh

# Todo: Uncomment before merge or to run in CodeBuild or to rebuild locally after changes
# ./regression_tests/stages/build_platform_helper.sh

# Todo: Uncomment before merge or to run in CodeBuild or to re-clone locally
# ./regression_tests/stages/clone_demodjango_deploy.sh

# Todo: Uncomment before merge or to run in CodeBuild or to re-clone locally
# ./regression_tests/stages/clone_demodjango.sh

./regression_tests/stages/run_platform_helper_environment_generate.sh

./regression_tests/stages/run_platform_helper_generate.sh

# Todo: DBTP-1073 Include deploying environment pipelines in regression tests

# Todo: DBTP-1074 Include deploying codebase pipelines in regression tests

# Todo: Uncomment before merge or to run in CodeBuild
# ./regression_tests/stages/run_environment_pipeline.sh

# Todo: Uncomment before merge or to run in CodeBuild
# ./regression_tests/stages/run_codebase_pipeline.sh

./regression_tests/stages/run_demodjango_smoke_tests.sh

./regression_tests/stages/run_maintenance_page_tests.sh

# Todo: DBTP-1076 Ensure regression tests builds run one at a time

# Todo: DBTP-1075 Trigger regression tests off all four main DBT Platform Codebases
