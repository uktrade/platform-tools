#!/bin/bash

# exit early if something goes wrong
set -e

PYPI_TOKEN=$1
VERSION=$(python utils/check_pypi.py --version)

export SLACK_TOKEN=$2
export SLACK_CHANNEL_ID=$3

# if ! python utils/check_pypi.py
# then
  # echo Building Python package
  # poetry build
  # echo Publishing Python package ${VERSION}
  # poetry config pypi-token.pypi ${PYPI_TOKEN}
  # poetry publish
  # echo Checking the package has reached PyPI
  # python utils/check_pypi.py --max-attempts 20
  echo -e "\nSending slack notification"
  VERSION_NUMBER=($VERSION)
  python utils/notify/publish_notification.py --publish-version ${VERSION_NUMBER[1]}
# else
#   echo ${VERSION} of the package has already been published
# fi
