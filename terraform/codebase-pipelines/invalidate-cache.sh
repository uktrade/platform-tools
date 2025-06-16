#!/bin/bash
# PATHS will be passed in as an argument
PATHS="/frontend/* /admin/*"

DISTRIBUTION=$(aws cloudfront list-distributions --query 'DistributionList.Items' --output json | jq -r --arg domain ${1} '.[] | select(.Aliases.Items[0] == $domain) | .Id')

echo -e "\nInvalidating the cache for paths ${PATHS}\n"

aws cloudfront create-invalidation \
    --distribution-id $DISTRIBUTION \
    --paths $PATHS

# With a list of domains:
# export DOMAINS='["api.kate.demodjango.uktrade.digital", "web.kate.demodjango.uktrade.digital"]'

# aws cloudfront list-distributions --query 'DistributionList.Items' --output json | jq -r --argjson domains "${DOMAINS}" '.[] | select(.Aliases.Items[0] as $d | $domains | index($d)) | .Id'
