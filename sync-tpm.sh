#!/usr/bin/env bash

rsync -cav --delete --exclude ".terraform*" ../terraform-platform-modules/* terraform/

sed -i 's#git::ssh://git@github.com/uktrade/terraform-platform-modules.git//extensions?depth=1&ref=#git::ssh://git@github.com/uktrade/platform-tools.git//terraform/extensions?depth=1\&ref=#' terraform/README.md
sed -i 's/# Terraform Platform Modules/# Terraform used by Platform-tools/' terraform/README.md

sed -i 's%# checkov:skip=CKV2_AWS_28: WAF is outside of terraform-platform-modules%# checkov:skip=CKV2_AWS_28: WAF is outside of platform-tools/terraform%' terraform/application-load-balancer/main.tf

rm terraform/CHANGELOG.md
rm terraform/codecov.yml
rm terraform/poetry.lock
rm terraform/pyproject.toml
rm terraform/release-config.json
