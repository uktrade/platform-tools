# Copilot Tools 

![](https://codebuild.eu-west-2.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiS2t1L3UvQmVTbXZsOTVIOWxGanpwTTh4b3BNcUR4c0dNN2NoSUpGcVkzN0JEOFpvc2kwL2pGVC91TXNVcjFNK0d5eExia0R2SS9lZUhuWTZQOTlieVY0PSIsIml2UGFyYW1ldGVyU3BlYyI6Im5tS0pUVEwvT204WXdxT2wiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=main)

## Using the dbt-copilot-tools package

See [the package documentation](https://github.com/uktrade/copilot-tools/blob/main/commands/README.md) for detail on what the package is and how to use it.

If you are migrating a service to DBT PaaS, [GOV.UK PaaS to DBT PaaS Migration](https://github.com/uktrade/platform-documentation/blob/main/gov-pass-to-copilot-migration/README.md) will also be relevant for you.

## Contributing to the dbt-copilot-tools package

### Getting started

1. Clone the repository:

   ```
   git clone https://github.com/uktrade/copilot-tools.git && cd copilot-tools
   ```

2. Install the required dependencies:

   ```
   pip install poetry && poetry install && poetry run pre-commit install
   ```

### Testing

Run `poetry run pytest` in the root directory to run all tests.

Or, run `poetry run tox` in the root directory to run all tests for multiple Python versions. See the [`tox` configuration file](tox.ini).

#### [`Dockerfile.test`](Dockerfile.test)

This `Dockerfile` is used to create a Docker image that supports multiple versions of Python runtimes via [`pyenv`](https://github.com/pyenv/pyenv). The `tox` configuration file determines the Python versions to be tested against.

#### Adding a Python version

Add the Python version(s) to `Dockerfile.test` and `tox.ini`.

Run `docker build -f Dockerfile.test -t alpine/python .` to build the image.

For Platform developers, the `push` commands can be found in [AWS ECR](https://eu-west-2.console.aws.amazon.com/ecr/repositories).

### Publishing

To publish the Python package `dbt-copilot-tools`, you will need an API token.

1. Acquire API token from [Passman](https://passman.ci.uktrade.digital/secret/cc82a3f7-ddfa-4312-ab56-1ff8528dadc8/).
   - Request access from the SRE team.
   - _Note: You will need access to the `platform` group in Passman._
2. Run `poetry config pypi-token.pypi <token>` to add the token to your Poetry configuration.

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
