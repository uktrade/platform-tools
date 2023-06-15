# Copilot Tools 

![](https://codebuild.eu-west-2.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiZG51SVRBNWhrbm1PSkZmeEdKbjN2SGRGRllPTUplR1JUbkRpa3NsOUNaR3JyZkF4SXFaOTNqck03SUtjbTgveXR6aEcvMDZkNlNBYUsxbHYwT0lWa3ZZPSIsIml2UGFyYW1ldGVyU3BlYyI6IlZVOGJqelpxT2hydFE5S2kiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=main)

This repository contains a set of tools for transferring applications/services from [GOV.UK PaaS](https://www.cloud.service.gov.uk) to DBT PaaS which augments [AWS Copilot](https://aws.github.io/copilot-cli/) to improve the developer and SRE experience.

## Getting started

1. Clone the repository:

   ```
   git clone https://github.com/uktrade/copilot-tools.git && cd copilot-tools
   ```

2. Install the requirements

   ```
   pip install poetry && poetry install --with pre-commit && pre-commit install
   ```

## Testing

Run `poetry run pytest` in the root directory to run all tests.

Or, run `poetry run tox` in the root directory to run all tests for multiple Python versions. See the [`tox` configuration file](tox.ini).

## Migration

See [GOV.UK PaaS to DBT PaaS Migration](https://github.com/uktrade/platform-documentation/blob/main/gov-pass-to-copiltot-migration/README.md).
