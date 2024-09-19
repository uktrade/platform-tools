# Platform Tools

![](https://codebuild.eu-west-2.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiS2t1L3UvQmVTbXZsOTVIOWxGanpwTTh4b3BNcUR4c0dNN2NoSUpGcVkzN0JEOFpvc2kwL2pGVC91TXNVcjFNK0d5eExia0R2SS9lZUhuWTZQOTlieVY0PSIsIml2UGFyYW1ldGVyU3BlYyI6Im5tS0pUVEwvT204WXdxT2wiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=main)

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

2. Install the required dependencies:

   ```
   pip install poetry && poetry install && poetry run pre-commit install
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

#### Regression tests

Amongst other things designed to exercise our tools together, the regression tests will attempt to deploy `demodjango` to the `toolspr` environment and run the smoke tests.

At present, this is currently only triggered on merges to the `main` branch for this code base and on a schedule early every morning.

You can manually trigger a run from the `platform-tools-test` AWS CodeBuild project.

To test your `platform-tools` changes before merging, use "Start build with overrides" and set the "Source version" to your branch name.

You may wish to run tests against a `demodjango` environment other than `toolspr`. 

In order for this to work, you will need to have deployed environment and codebase pipelines for your environment. See the `toolspr` examples in [demodjango-deploy/platform-config.yml](https://github.com/uktrade/demodjango-deploy/blob/main/platform-config.yml).

To run the regression tests against your environment, select "Start build with overrides", navigate to "Additional configuration" in the "Environment" section, and set `TARGET_ENVIRONMENT` environment variable value to your environment name.

To run the regression test against a specific branch for demodjango and demodjango-deploy you can use the "Start build with overrides" and add the following variables to "Additional configuration" in the "Environment" section.  `DEMODJANGO_DEPLOY_BRANCH` or `DEMODJANGO_BRANCH`.  However to ensure the ci-image-builder also used that same branch for demodjango image build, you will need to also add the VAR `DEPLOY_REPOSITORY_BRANCH` to the `pipeline-demodjango-application-<env>\DeployTo-<env>` in the platform-sandbox account.

Because we are currently targeting the same environment for all runs and AWS CodeBuild does not support queueing, it is essential that we do not start a regression test run while another is in progress, communicate with the team and check in the `platform-tools-test` AWS CodeBuild project.

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

- Merging to `main` will trigger a CodeBuild project called `platform-tools-test` in the _platform-tools_ AWS account to run regression tests on `merge to main / pull request created / pull request updated` events emitted by GitHub
- We use the `release-please` GitHub action to create and update a _release PR_ when changes are merged to `main`
  - The _release PR_ will automatically update the _pyproject.toml_ version number and generate release notes based on the commits merged since the last release
  - Merging the _release PR_ will create a draft GitHub release for the next version with release notes

#### Publishing GitHub release

Publishing a GitHub release should automatically:

- Run the full regression pipeline (currently WIP)
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

