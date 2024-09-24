#!/bin/bash

run_command () {
   echo -e "\nRunning command: $1"
   $1
}

run_checks() {
    run_command "echo $VIRTUAL_ENV"
    run_command "python --version"
    run_command "which python"
    run_command "which pip"
    run_command "pip install --upgrade pip"
    run_command "which pip"
    run_command "pip list"
    run_command "pip install --upgrade schema"
    run_command "pip list"
}

run_command "cd regression_tests"

run_command "rm -rf venv_temp*"

echo -e "\n\nDo venv1"
run_command "python -m venv --copies venv_temp1/venv"
sedcmd=(sed -i '' '45s/.*/VIRTUAL_ENV="$(cd "$(dirname "$(dirname "${BASH_SOURCE[0]}" )")" \&\& pwd)"/' venv_temp1/venv/bin/activate)
"${sedcmd[@]}"
sedcmd=(sed -i '' '1s/.*/#!\/usr\/bin\/env python/' venv_temp1/venv/bin/pip*)
"${sedcmd[@]}"
run_command "source venv_temp1/venv/bin/activate"
run_checks

#echo -e "\n\nDeactivate venv1"
#run_command "deactivate"
#run_command "which python"
#run_command "which pip"

echo -e "\n\nDo venv2"
#run_command "python -m venv --copies venv_temp2/venv"
#run_command "rm -rf venv_temp2/venv/lib"
run_command "cp -R venv_temp1 venv_temp2"
#run_command "rm -rf venv_temp1"
run_command "source venv_temp2/venv/bin/activate"
run_checks
