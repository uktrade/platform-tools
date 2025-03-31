#!/usr/bin/env bash

rsync -r --exclude ".terraform*" ../terraform-platform-modules/* terraform/

for f in $(git status --porcelain | grep "^ M" | sed 's/^ M //')
do
  sed -i 's/source( *= *)"git::ssh://git@github.com/uktrade/platform-tools.git//terraform/extensions\?depth=1&ref="/source$1"git::ssh://git@github.com/uktrade/terraform-platform-modules.git//extensions\?depth=1&ref="/' "$f"
done

