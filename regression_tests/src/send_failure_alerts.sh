#!/bin/bash

echo "TARGET_ENVIRONMENT: ${TARGET_ENVIRONMENT}"

function is_everything_on_branch_main() {
    git branch --contains $CODEBUILD_RESOLVED_SOURCE_VERSION | grep -q "main"

    cd demodjango-deploy
    git branch --contains $CODEBUILD_RESOLVED_SOURCE_VERSION | grep -q "main"
    cd "$CODEBUILD_SRC_DIR"

    cd demodjango
    git branch --contains $CODEBUILD_RESOLVED_SOURCE_VERSION | grep -q "main"
    cd "$CODEBUILD_SRC_DIR"

    #todo: Add terraform-platform-tools when we are targeting branches
}

if [ "${CODEBUILD_BUILD_SUCCEEDING}" != "1" ] && \
    is_everything_on_branch_main && \
    [ "${TARGET_ENVIRONMENT:-toolspr}" == "tony" ]; then

    echo -e "\nAction failed sending alert"
    pip install dbt-platform-helper
    MESSAGE=":alert: @here DBT Platform regression tests have failed in <https://eu-west-2.console.aws.amazon.com/codesuite/codebuild/763451185160/projects/platform-tools-test/build/${CODEBUILD_BUILD_ID}/?region=eu-west-2|build ${CODEBUILD_BUILD_NUMBER}> :sob:"
    platform-helper notify add-comment "${SLACK_CHANNEL_ID}" "${SLACK_TOKEN}" "" "${MESSAGE}"
else
    echo -e "\nAction succeeded, no alert sent"
fi
