# Copilot Tools 

![](https://codebuild.eu-west-2.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiZG51SVRBNWhrbm1PSkZmeEdKbjN2SGRGRllPTUplR1JUbkRpa3NsOUNaR3JyZkF4SXFaOTNqck03SUtjbTgveXR6aEcvMDZkNlNBYUsxbHYwT0lWa3ZZPSIsIml2UGFyYW1ldGVyU3BlYyI6IlZVOGJqelpxT2hydFE5S2kiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=main)

This repository contains a set of tools for transferring applications/services from GOV.UK PaaS to DBT PaaS.

## Getting started

1. Clone the repository:

   ```
   git clone https://github.com/uktrade/copilot-tools.git && cd copilot-tools
   ```

2. Install the requirements

   ```
   pip install pip-tools && pip-sync requirements/dev.txt && pre-commit install
   ```

## Testing

Run `pytest` in the root directory to run all tests.

## Migration

See [GOV.UK PaaS to DBT PaaS Migration](https://github.com/uktrade/platform-documentation/blob/main/gov-pass-to-copiltot-migration/README.md).
