#!/bin/bash 

set -e

echo -e "\nRun platform-helper environment generate"
cd ./demodjango-deploy/
# The command is run elsewhere in pipelines, but this gives us faster, more granular feedback
AWS_PROFILE=platform-sandbox PLATFORM_TOOLS_SKIP_VERSION_CHECK=true platform-helper environment generate --name toolspr --vpc-name platform-sandbox-dev
cd ..
