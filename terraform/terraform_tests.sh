#!/usr/bin/env bash

unit_test_files=$(find . -name "*tftest.hcl" | grep -v e2e-tests | sort)
modules=""
IFS=$'\n'
for file in $unit_test_files
do
  # Lose leading ./ and select the part before the tests directory
  module=$(echo "${file#./}" | awk -F "/tests/" '{print $1}')
  # In case we separate the test files, only include each module once
  if [[ "\"${modules}\"" != *"\"${module}\""* ]]; then
    message="Running tests for module ${module}"
    underline=$(echo "${message}" | sed "s/./=/g")
    echo -en "\n\033[1;36m${message}\033[0m"
    echo -e "\n\033[1;36m${underline}\033[0m"
    pushd "${module}"
    terraform init
    terraform test
    popd
  fi
done
