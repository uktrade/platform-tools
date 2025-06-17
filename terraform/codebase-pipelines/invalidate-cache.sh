#!/bin/bash
CONFIG=${1}

CONFIG='"{\"web.kate.demodjango.uktrade.digital\":[\"/hello/*\", \"/goodbye/*\"], \"api.kate.demodjango.uktrade.digital\":[\"/hello/*\", \"/goodbye/*\"]}"'

DOMAINS=$(echo $CONFIG | jq -r 'fromjson | keys[]')

for i in ${DOMAINS}; do
    echo "Getting distribution ID for domain ${i}"
    DISTRIBUTION_ID=$(aws cloudfront list-distributions --query 'DistributionList.Items' --output json | jq -r --arg domain ${i} '.[] | select(.Aliases.Items[0] == $domain) | .Id')
    PATHS=$(echo $CONFIG | jq -r --arg domain ${i} 'fromjson | .[$domain] | join(" ")')
    echo -e "\nInvalidating the cache in distibution id ${DISTRIBUTION_ID} for paths ${PATHS}\n"
done
