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

replace_static_path_in_venv_activate() {
    static_path="\"$(pwd)/venv_temp1/venv\""
    dynamic_path='"$(cd "$(dirname "$(dirname "${BASH_SOURCE[0]}" )")" \&\& pwd)"'
    sedcmd=(sed -i '' "s|${static_path}|${dynamic_path}|g" venv_temp1/venv/bin/activate)
    "${sedcmd[@]}"
}

replace_static_paths_in_shebangs_etc() {
    # static_path="/codebuild/output/src[^/]+/src/codestar-connections.eu-west-2.amazonaws.com/git-http/763451185160/eu-west-2/[^/]+/uktrade/platform-tools/venv"
    # todo: lose the hardcoded venv_temp1 in old path
    old_path="/Users/willgibson/Dev/DBT/uktrade/platform-tools/regression_tests/venv_temp1/venv"
    new_path="/Users/willgibson/Dev/DBT/uktrade/platform-tools/regression_tests/venv_temp2/venv"
    files=$(grep -RiIl "$old_path" venv_temp2/venv)
    while IFS= read -r file; do
        sedcmd=(sed -i '' "s|$old_path|$new_path|g" "$file")
        "${sedcmd[@]}"
    done <<< "$files"
}

run_command "cd regression_tests"

run_command "rm -rf venv_temp*"

echo -e "\n\nDo venv1"
run_command "python -m venv --copies venv_temp1/venv"
run_command "replace_static_path_in_venv_activate"
run_command "source venv_temp1/venv/bin/activate"
run_checks

echo -e "\n\nDeactivate venv1"
run_command "deactivate"
run_command "which python"
run_command "which pip"

echo -e "\n\nDo venv2"
run_command "mv venv_temp1 venv_temp2"
run_command "replace_static_paths_in_shebangs_etc"
run_command "source venv_temp2/venv/bin/activate"
run_checks
