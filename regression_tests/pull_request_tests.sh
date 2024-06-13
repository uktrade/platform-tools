#!/bin/bash

# exit early if something goes wrong
set -e

./regression_tests/stages/build_platform_helper.sh

./regression_tests/stages/clone_demodjango_deploy.sh

./regression_tests/stages/set_up_aws_config.sh

./regression_tests/stages/run_platform_helper_environment_generate.sh

./regression_tests/stages/run_platform_helper_generate.sh

./regression_tests/stages/run_environment_pipeline.sh

# echo -e "\nDeploy services"
# (ideally with pipeline)
# platform-helper codebase deploy --app demodjango --env toolspr --codebase application --commit <commit_hash>
# In the meantime, run the following from the demodjango-deploy codebase on your machine...
#   IMAGE_TAG=tag-latest copilot svc deploy --name celery-worker --env toolspr
#   IMAGE_TAG=tag-latest copilot svc deploy --name celery-beat --env toolspr
#   IMAGE_TAG=tag-latest copilot svc deploy --name web --env toolspr

# echo -e "\nRun smoke tests"
# From the demodjango codebase on your machine, run...
#   ./smoke_tests.sh toolspr

# Update trigger to run it from all four codebases on merge to main

# Todo: Slack alert if it fails on the main branch
