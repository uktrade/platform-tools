# Copilot Tools 

![](https://codebuild.eu-west-2.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoicUFCMXNSZVVUdnJuLzNHMDJlUVg4UVErbFkwT1NKa0NubUNudm9STk5makxZYUdtK0xiSmgxWXUzWUttTTdPbnprdTFVY2FJUzZXbHIyQTVkYmJtaVNJPSIsIml2UGFyYW1ldGVyU3BlYyI6IkxYaUFJczFoQitodytUTHAiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=main)

This repository contains a set of tools for transferring applications/services from [GOV.UK PaaS](https://www.cloud.service.gov.uk) to DBT PaaS which augments [AWS Copilot](https://aws.github.io/copilot-cli/) to improve the developer and SRE experience.

## Getting started

1. Clone the repository:

   ```
   git clone https://github.com/uktrade/copilot-tools.git && cd copilot-tools
   ```

2. Install the required dependencies:

   ```
   pip install poetry && poetry install --with pre-commit && pre-commit install
   ```

## Testing

Run `poetry run pytest` in the root directory to run all tests.

Or, run `poetry run tox` in the root directory to run all tests for multiple Python versions. See the [`tox` configuration file](tox.ini).

### [`Dockerfile.test`](Dockerfile.test)

This `Dockerfile` is used to create a Docker image that supports multiple versions of Python runtimes via [`pyenv`](https://github.com/pyenv/pyenv). The `tox` configuration file determines the Python versions to be tested against.

#### Adding a Python version

Add the Python version(s) to `Dockerfile.test` and `tox.ini`.

Run `docker build -f Dockerfile.test -t alpine/python .` to build the image.

For Platform developers, the `push` commands can be found in [AWS ECR](https://eu-west-2.console.aws.amazon.com/ecr/repositories).

## Migration

See [GOV.UK PaaS to DBT PaaS Migration](https://github.com/uktrade/platform-documentation/blob/main/gov-pass-to-copiltot-migration/README.md).
