# Migration tools

Scripts used to determine application configuration by retrieving current pipeline configurations and GOV.UK PaaS data,
such as environments, environment variables, domains, certificates, etc.

## Using the tools

### `get-ci-config.py`

Combines the `ci-pipeline-config` YAML files based on the namespace field and outputs `ci-config.yml`.

    ./migration-tools/get-ci-config.py

Make sure the first line in `ci-config.yml` begins with `applications` instead of `dictitems`, removing any lines above that refer to `python`.

### `get-paas-config.py`

Retrieves GOV.UK PaaS data and outputs `paas-config.yml`.

* You need to have admin access etc. on all the things in all the GOV.UK PaaS organisations and spaces for this to work.
* You will need to log into [Cloud Foundry CLI](https://docs.cloudfoundry.org/cf-cli/); the scripts pick up the access
  key in `~/.cf/config.json`.

    ./migration-tools/get-paas-config.py

### `combine-ci-paas-config.py`

Combines the two previous generated files and outputs `full-config.yml`.

    ./migration-tools/combine-ci-paas-config.py

### `build-copilot-config.py`

Takes `full-config.yml` and generates individual boostrap configuration input files in the `bootstrap-config` directory.
The format of the filenames: `<namespace>-copilot.yml`.

    ./migration-tools/build-copilot-config.py

See [`bootstrap-config`](../bootstrap-config/) for the output.
