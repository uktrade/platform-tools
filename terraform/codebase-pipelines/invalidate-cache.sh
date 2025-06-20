#!/bin/bash
CONFIG=${1}

ENV_CONFIG='"{\"dev\": {\"account\":\"1234\",\"dns_account\":\"4567\"}, \"prod\": {\"account\":\"0987\",\"dns_account\":\"4444\"}}"'
CONFIG_JSON='"{\"web.kate.demodjango.uktrade.digital\":[\"/hello/*\", \"/goodbye/*\"], \"api.kate.demodjango.uktrade.digital\":[\"/hello/*\", \"/goodbye/*\"]}"'
DNS_ACCOUNT_ID=$(echo $ENV_CONFIG | jq -r --arg env ${ENVIRONMENT} 'fromjson | .[$env].dns_account')

CONFIG='"{\"kate\":{\"web.kate.demodjango.uktrade.digital\":[\"/hello/*\", \"/goodbye/*\"], \"api.kate.demodjango.uktrade.digital\":[\"/hello/*\", \"/goodbye/*\"]},
\"david\":{\"web.david.demodjango.uktrade.digital\":[\"/hola/*\", \"/adios/*\"], \"api.david.demodjango.uktrade.digital\":[\"/hola/*\", \"/adios/*\"]}}"'

ENV_CONFIG=$(echo $CONFIG | jq -r --arg env ${ENVIRONMENT} 'fromjson | .[$env]')
DOMAINS=$(echo $ENV_CONFIG | jq -r 'fromjson | keys[]')

for i in ${DOMAINS}; do
    echo "Getting distribution ID for domain ${i}"
    DISTRIBUTION_ID=$(aws cloudfront list-distributions --query 'DistributionList.Items' --output json | jq -r --arg domain ${i} '.[] | select(.Aliases.Items[0] == $domain) | .Id')
    PATHS=$(echo $CONFIG | jq -r --arg domain ${i} 'fromjson | .[$domain] | join(" ")')
    echo -e "\nInvalidating the cache in distibution id ${DISTRIBUTION_ID} for paths ${PATHS}\n"
    aws cloudfront create-invalidation \
    --distribution-id $DISTRIBUTION_ID \
    --paths $PATHS
done
