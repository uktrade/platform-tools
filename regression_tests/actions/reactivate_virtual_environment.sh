#!/bin/bash

set -e

echo -e "\n\n### Reactivate virtual environment\n"

source ./regression_tests/src/venv_helper.sh

fix_paths_and_activate_venv
