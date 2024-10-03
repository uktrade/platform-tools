#!/bin/bash

set -e

echo -e "\n\n### Create virtual environment\n"

source ./regression_tests/src/venv_helper.sh

create_and_activate_venv
