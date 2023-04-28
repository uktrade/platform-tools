# Migration tools

## Requirements

## Using the tools

### get-ci-config.py

Combines the ci-pipeline-config yaml files based on the namespace field and output `ci-config.yml`.

    ./migration-tools/get-ci-config.py

Make sure the first line in `ci-config.yml` begins with `applications`, removing any lines with reference to `python`.

### get-paas-config.py

Retrieves Gov.UK PaaS data and outputs `paas-config.yml`.

* You need to have admin etc. on all the things in all the Gov.uk PaaS organisations and space for this to work fully. 
* You will need to log into [Cloud Foundry CLI](https://docs.cloudfoundry.org/cf-cli/), the scripts pick up the access key in `~/.cf/config.json`.

    ./migration-tools/get-paas-config.py

### combine-ci-paas-config.py

Combines the previous two files and outputs `full-config.yml`.

    ./migration-tools/combine-ci-paas-config.py

### build-copilot-config.py

Takes `full-config.yml` and renders individual copilot-bootstrap input files.

    ./migration-tools/build-copilot-config.py

See [`bootstrap-config`](../bootstrap-config/) for the output.
