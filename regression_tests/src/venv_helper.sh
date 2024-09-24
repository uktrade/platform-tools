#!/bin/bash

function create_and_activate_venv() {
    python -m venv --copies venv
    write_static_path_to_file
    replace_static_path_in_venv_activate
    source venv/bin/activate
    run_checks
}

function fix_paths_and_activate_venv() {
    replace_static_paths_in_shebangs_etc
    source venv/bin/activate
    run_checks
}

run_checks() {
    echo "Running checks"
    echo "VIRTUAL_ENV: $VIRTUAL_ENV"
    echo "Python version: $(python --version)"
    echo "Which Python: $(which python)"
    echo "Which pip: $(which pip)"
    echo "pip list: $(pip list)"
}

write_static_path_to_file() {
    static_path="$(pwd)/venv"
    echo "$static_path" > "${static_path}/.venv_path"
}

get_old_path() {
    cat venv/.venv_path
}

replace_static_path_in_venv_activate() {
    static_path="\"$(get_old_path)\""
    dynamic_path='"$(cd "$(dirname "$(dirname "${BASH_SOURCE[0]}" )")" \&\& pwd)"'
    sedcmd=(sed -i "s|${static_path}|${dynamic_path}|g" venv/bin/activate)
    "${sedcmd[@]}"
}

replace_static_paths_in_shebangs_etc() {
    old_path="$(get_old_path)"
    new_path="$(pwd)/venv"
    echo "Replacing $old_path with $new_path"
    files=$(grep -RiIl "$old_path" "$new_path")
    while IFS= read -r file; do
        sedcmd=(sed -i '' "s|$old_path|$new_path|g" "$file")
        "${sedcmd[@]}"
    done <<< "$files"
}
