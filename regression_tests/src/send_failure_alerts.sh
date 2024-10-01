#!/bin/bash

echo "TARGET_ENVIRONMENT: ${TARGET_ENVIRONMENT}"

if [ "${CODEBUILD_BUILD_SUCCEEDING}" != "1" ] && git branch --contains $CODEBUILD_RESOLVED_SOURCE_VERSION | grep -q "1291-sort-out-alerts" && [ "${TARGET_ENVIRONMENT:-toolspr}" == "tony" ]; then
    echo -e "\nAction failed sending alert"
    pip install dbt-platform-helper
    MESSAGE=":alert: @here DBT Platform regression tests have failed in <https://eu-west-2.console.aws.amazon.com/codesuite/codebuild/763451185160/projects/platform-tools-test/build/${CODEBUILD_BUILD_ID}/?region=eu-west-2|build ${CODEBUILD_BUILD_NUMBER}> :sob:"
    platform-helper notify add-comment "${SLACK_CHANNEL_ID}" "${SLACK_TOKEN}" "" "${MESSAGE}"
else
    echo -e "\nAction succeeded, no alert sent"
fi
