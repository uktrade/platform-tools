#!/bin/bash

echo -e "\nBuild and install platform-helper"
poetry build --no-interaction --format sdist --no-ansi
pip install "dist/$(ls -t1 dist | head -1)"
platform-helper --version
