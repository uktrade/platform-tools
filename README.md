# Platform Tools

## Using the dbt-platform-helper package

See [the package documentation](https://github.com/uktrade/platform-tools/blob/main/dbt_platform_helper/README.md) for detail on what the package is and how to use it.

If you are migrating a service to DBT PaaS, [GOV.UK PaaS to DBT PaaS Migration](https://github.com/uktrade/platform-documentation/blob/main/docs/playbooks/migrating-from-govuk-paas/migration-guide.md) will also be relevant for you.

### Supported Python versions

3.9, 3.10, 3.11 and 3.12.

## Contributing to the dbt-platform-helper package

### Getting started

1. Clone the repository:

   ```
   git clone https://github.com/uktrade/platform-tools.git && cd platform-tools
   ```

2. Install dependencies:

    ```shell
    pip install poetry && poetry install
    ```
   
3. Install Trufflehog for the pre-commit hook:

    ```shell
    # Installation on Mac
    
    brew install trufflehog
    ```

   Alternative installation methods [here](https://github.com/trufflesecurity/trufflehog)

4. Install pre-commit hook:

    ```shell
    poetry run pre-commit install
    ```

### Testing

#### Requirements

The following tools are required to run the full test suite.

- [checkov](https://www.checkov.io/)
- [AWS Copilot](https://aws.github.io/copilot-cli/)

#### Unit tests

Run `poetry run pytest` in the root directory to run all tests.

Or, run `poetry run tox` in the root directory to run all tests for multiple Python versions. See the [`tox` configuration file](tox.ini).

Note: by default the tests are run using multiple processes for speed. When running using multiple processes pdb (python debugger) does not play nicely and will error.

To allow pdb to work correctly, disable multiple processes using the `--numprocesses 0` option:

`poetry run pytest --numprocesses 0`

We use [Codecov](https://app.codecov.io/github/uktrade/platform-tools) to monitor the comprehensiveness and performance of our unit tests.

#### Manual testing

You may want to test any CLI changes locally.

##### Option 1 - Build and install `platform-helper` from your local source code

Run `poetry build` to build your package resulting in a package file (e.g. `dbt_platform_tools-0.1.40.tar.gz`) in a `dist` folder. You may need to bump up the package version before doing so. To bump the version go to `pyproject.toml/version`

Copy the package file(s) to the directory where you would like to test your changes, and make sure you are in a virtual environment. Run `platform-helper --version` to check the installed package version (e.g. `0.1.39`).

> [!NOTE]
> Copying the package file is optional, but recommended. You can keep the package file in the `dist` folder and install the package from your directory.

Run `pip install <file>` and confirm the installation has worked by running `platform-helper --version` which would output version `0.1.40` following our example.

> [!IMPORTANT]
> When testing is complete, do not forget to revert the `dbt-platform-helper` installation back to what it was; e.g. `pip install dbt-platform-helper==0.1.39`.

##### Option 2 - Run the python files directly.

This assumes that the virtual python environment where you are running them from already has the dependencies installed and the directory is at the same level as your platform-tools directory.

Example usage:

```
# From <application>-deploy

../platform-tools/platform_helper.py <command> <options>
```


#### End to end testing

Because this codebase is only fully exercised in conjunction with several others, we have [platform-end-to-end-tests](https://github.com/uktrade/platform-end-to-end-tests), which orchestrates the testing of them working together.

### Publishing

Publishing to PyPI happens automatically when a GitHub Release is published. To publish the Python package `dbt-platform-helper` manually, you will need an API token.

1. Acquire API token from [Passman](https://passman.ci.uktrade.digital/secret/cc82a3f7-ddfa-4312-ab56-1ff8528dadc8/).
   - Request access from the SRE team.
   - _Note: You will need access to the `platform` group in Passman._
2. Run `poetry config pypi-token.pypi <token>` to add the token to your Poetry configuration.

Update the version, as the same version cannot be published to PyPI.

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

Check the [PyPI Release history](https://pypi.org/project/dbt-platform-helper/#history) to make sure the package has been updated.

For an optional manual check, install the package locally and test everything works as expected.

## Releases

### Release structure

- Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) in our pull request titles. These become the release commit messages in the `main` branch. The advantage of this is that it's clear from a list of commits, what kind of changes they include (_fix=patch, feat=minor, !=breaking change_) and most importantly whether commits include breaking changes
- Use [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository) to document and manage releases
- Non-breaking changes already in the `main` branch should be released before merging a breaking change
- Minor and patch releases should always include zero downtime
- Documentation for releases with breaking changes should include the upgrade path
- Where possible the upgrade path should allow for zero downtime, if this is not possible, it should be flagged up big and visible

### Release Automation

#### Merging to main

- Merging to `main` will trigger the `pull-request-end-to-end-tests` pipeline in the _platform-tools_ AWS account to run regression tests
- We use the `release-please` GitHub action to create and update a _release PR_ when changes are merged to `main`
  - The _release PR_ will automatically update the _pyproject.toml_ version number and generate release notes based on the commits merged since the last release
  - Merging the _release PR_ will create a draft GitHub release for the next version with release notes

#### Publishing GitHub release

Publishing a GitHub release should automatically:

- Run the full `pull-request-end-to-end-tests` pipeline
- Trigger a CodeBuild project called `platform-tools-build` in the _platform-tools_ AWS account to run. This runs the _buildspec-pypi.yml_ file which contains the build steps to publish the new `platform-helper` package version to PyPI
- Trigger a rebuild of the DBT Platform Documentation, so it includes the latest release documentation (currently WIP)
- Push a notification to the development community via the #developers channel in Slack

#### Publishing to PyPI

Successful completion of the CodeBuild project `platform-tools-build` in the _platform-tools_ AWS account executes the _buildspec-pypi.yml_ file which publishes the new application version to PyPI. This build process involves the following steps:

- Retrieving a list of prior releases from the `dbt-platform-helper` PyPI project repository.
- Verifying if the `dbt-platform-helper` package version in the root _pyproject.toml_ file does not exist in the list of releases obtained from PyPI.
- If the version does not exist in the PyPI release list, the application is built and published to PyPI as a new release with the version stated in the application _pyproject.toml_ file
- Next the script again checks if the updated version number is included in the PyPI release list.
If found, it indicates that the new package version exists in PyPI.
- A Slack message is sent to the `#developers` channel to notify others that the platform-helper tool has been updated

### Release procedure

1. Work on a new branch
2. Create a PR and have it reviewed
3. Once approved:
   - If it is a breaking change, you must release any outstanding non breaking changes before merging
   - Merge to `main`
5. A _release PR_ will automatically be created when changes are merged to main
   - The _release PR_ is updated with next version number and release notes based on the commits since the last release
6. Merge the _release PR_ to create a GitHub release
7. Ensure the release notes contain an upgrade path for any breaking changes
8. Check PyPI for the new published version

