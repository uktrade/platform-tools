#!/bin/bash

      - echo -e "\n\n-----------------OLD PATH REPLACE------------------------------"
      # Find and replace all occurrences of old paths in the restored venv
      - OLD_PATH_PATTERN="/codebuild/output/src[^/]+/src/codestar-connections.eu-west-2.amazonaws.com/git-http/763451185160/eu-west-2/[^/]+/uktrade/platform-tools/venv"

      # Replace any instance of old paths in the 'venv' folder with the new one
      - find venv/ -type f -exec sed -i "s|$OLD_PATH_PATTERN|$CONSTRUCTED_PATH|g" {} +
        # Update the activate script to use the new path
      - |
        find venv/bin/ -type f -name "activate*" -exec sed -i "
        s|^export VIRTUAL_ENV=.*|export VIRTUAL_ENV=\"$CONSTRUCTED_PATH\"|;
        s|^_OLD_VIRTUAL_PATH=.*|_OLD_VIRTUAL_PATH=\"$CONSTRUCTED_PATH\"|;
        s|^_OLD_VIRTUAL_PYTHONHOME=.*|_OLD_VIRTUAL_PYTHONHOME=\"$CONSTRUCTED_PATH\"|;
        " {} +

      - cat venv/bin/activate | grep "VIRTUAL_ENV="
