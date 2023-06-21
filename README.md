# Copilot Tools 

![](https://codebuild.eu-west-2.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoicUFCMXNSZVVUdnJuLzNHMDJlUVg4UVErbFkwT1NKa0NubUNudm9STk5makxZYUdtK0xiSmgxWXUzWUttTTdPbnprdTFVY2FJUzZXbHIyQTVkYmJtaVNJPSIsIml2UGFyYW1ldGVyU3BlYyI6IkxYaUFJczFoQitodytUTHAiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=main)

This repository contains a set of tools for transferring applications/services from [GOV.UK PaaS](https://www.cloud.service.gov.uk) to Department for Business and Trade (DBT) PaaS which augments [AWS Copilot](https://aws.github.io/copilot-cli/) to improve the developer and SRE experience.

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

## Publishing

To publish the Python package `dbt-copilot-tools`, you will need an API token.

1. Acquire credentials from [Passman for PyPi](https://passman.ci.uktrade.digital/secret/244eb2ad-245d-47d9-9f6a-95ee30810944/).
   - Request access from the SRE team.
2. Log in to [PyPi](https://pypi.org) with the above credentials. The MFA token will also be in Passman.
3. Navigate to [Account settings](https://pypi.org/manage/account/).
4. Create an API token and copy the token.
5. Run `poetry config pypi-token.pypi <token>` to add the token to your Poetry configuration.

Update the version, as the same version cannot be published to PyPi.

```
poetry version patch
```

More options for the `version` command can be found in the [Poetry documentation](https://python-poetry.org/docs/cli/#version). For example, for a minor version bump: `poetry version minor`.

Build the Python package.

```
poetry build
```

Publish the Python package.

_Note: Make sure your Pull Request (PR) is approved and contains the version upgrade in `pyproject.toml` before publishing the package._

```
poetry publish
```

Check the [PyPi Release history](https://pypi.org/project/dbt-copilot-tools/#history) to make sure the package has been updated.

For an optional manual check, install the package locally and test everything works as expected.

## Migration

See [GOV.UK PaaS to DBT PaaS Migration](https://github.com/uktrade/platform-documentation/blob/main/gov-pass-to-copiltot-migration/README.md).
