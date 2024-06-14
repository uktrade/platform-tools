#!/bin/bash

set -e

echo -e "\nRun platform-helper generate (which runs copilot make-addons & pipeline generate)"
cd ./demodjango-deploy/
# The commands are run elsewhere in pipelines, but this gives us faster, more granular feedback
PLATFORM_TOOLS_SKIP_VERSION_CHECK=true platform-helper generate
cd ..
