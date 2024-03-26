# Copilot Tools

![](https://codebuild.eu-west-2.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiS2t1L3UvQmVTbXZsOTVIOWxGanpwTTh4b3BNcUR4c0dNN2NoSUpGcVkzN0JEOFpvc2kwL2pGVC91TXNVcjFNK0d5eExia0R2SS9lZUhuWTZQOTlieVY0PSIsIml2UGFyYW1ldGVyU3BlYyI6Im5tS0pUVEwvT204WXdxT2wiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=main)

## Using the dbt-platform-helper package

See [the package documentation](https://github.com/uktrade/platform-tools/blob/main/dbt_platform_helper/README.md) for detail on what the package is and how to use it.

If you are migrating a service to DBT PaaS, [GOV.UK PaaS to DBT PaaS Migration](https://github.com/uktrade/platform-documentation/blob/e6e02e08d13d78fa1f1bd14f9a5a69f21a26005e/docs/playbooks/migrating-from-govuk-paas/migration-guide.md) will also be relevant for you.

### Supported Python versions

3.9, 3.10, 3.11 and 3.12.

## Contributing to the dbt-platform-helper package

### Getting started

1. Clone the repository:

   ```
   git clone https://github.com/uktrade/platform-tools.git && cd platform-tools
   ```

2. Install the required dependencies:

   ```
   pip install poetry && poetry install && poetry run pre-commit install
   ```

### Testing

#### Requirements

The following tools are required to run the full test suite.

- [checkov](https://www.checkov.io/)
- [AWS Copilot](https://aws.github.io/copilot-cli/)

#### Automated testing

Run `poetry run pytest` in the root directory to run all tests.

Or, run `poetry run tox` in the root directory to run all tests for multiple Python versions. See the [`tox` configuration file](tox.ini).

Note: by default the tests are run using multiple processes for speed. When running using multiple processes pdb (python debugger) does not play nicely and will error. 

To allow pdb to work correctly, disable multiple processes using the `--numprocesses 0` option:

`poetry run pytest --numprocesses 0`

#### Manual testing

You may want to test any CLI changes locally.

Run `poetry build` to build your package resulting in a package file (e.g. `dbt_platform_tools-0.1.40.tar.gz`) in a `dist` folder. You may need to bump up the package version before doing so.

Copy the package file(s) to the directory where you would like to test your changes, and make sure you are in a virtual environment. Run `platform-helper --version` to check the installed package version (e.g. `0.1.39`).

> [!NOTE]
> Copying the package file is optional, but recommended. You can keep the package file in the `dist` folder and install the package from your directory.

Run `pip install <file>` and confirm the installation has worked by running `platform-helper --version` which would output version `0.1.40` following our example.

> [!IMPORTANT]
> When testing is complete, do not forget to revert the `dbt-platform-helper` installation back to what it was; e.g. `pip install dbt-platform-helper==0.1.39`.

### Publishing

To publish the Python package `dbt-platform-helper`, you will need an API token.

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

Check the [PyPi Release history](https://pypi.org/project/dbt-platform-helper/#history) to make sure the package has been updated.

For an optional manual check, install the package locally and test everything works as expected.
