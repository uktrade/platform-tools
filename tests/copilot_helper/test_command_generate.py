import os
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner
from freezegun.api import freeze_time
from moto import mock_iam
from moto import mock_s3
from moto import mock_sts

from dbt_copilot_helper.commands.generate import generate
from tests.copilot_helper.conftest import EXPECTED_FILES_DIR
from tests.copilot_helper.conftest import FIXTURES_DIR
from tests.copilot_helper.conftest import assert_file_created_in_stdout
from tests.copilot_helper.conftest import mock_codestar_connections_boto_client

ADDON_CONFIG_FILENAME = "addons.yml"


@freeze_time("2023-08-22 16:00:00")
@patch("dbt_copilot_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch("dbt_copilot_helper.utils.aws.get_aws_session_or_abort")
@patch("dbt_copilot_helper.commands.pipeline.git_remote", return_value="uktrade/test-app-deploy")
@pytest.mark.parametrize(
    "addon_file, expected_env_addons, expected_service_addons, expect_db_warning",
    [
        (
            "s3_addons.yml",
            [
                "my-s3-bucket.yml",
                "my-s3-bucket-with-an-object.yml",
                "addons.parameters.yml",
                "monitoring.yml",
                "vpc.yml",
            ],
            [
                "appconfig-ipfilter.yml",
                "subscription-filter.yml",
                "my-s3-bucket.yml",
                "my-s3-bucket-with-an-object.yml",
                "my-s3-bucket-bucket-access.yml",
            ],
            False,
        ),
        (
            "opensearch_addons.yml",
            [
                "my-opensearch.yml",
                "my-opensearch-longer.yml",
                "addons.parameters.yml",
                "monitoring.yml",
                "vpc.yml",
            ],
            ["appconfig-ipfilter.yml", "subscription-filter.yml"],
            False,
        ),
        (
            "rds_addons.yml",
            ["my-rds-db.yml", "addons.parameters.yml", "monitoring.yml", "vpc.yml"],
            ["appconfig-ipfilter.yml", "subscription-filter.yml"],
            True,
        ),
        (
            "redis_addons.yml",
            ["my-redis.yml", "addons.parameters.yml", "monitoring.yml", "vpc.yml"],
            ["appconfig-ipfilter.yml", "subscription-filter.yml"],
            False,
        ),
        (
            "aurora_addons.yml",
            ["my-aurora-db.yml", "addons.parameters.yml", "monitoring.yml", "vpc.yml"],
            ["appconfig-ipfilter.yml", "subscription-filter.yml"],
            True,
        ),
        (
            "monitoring_addons.yml",
            ["monitoring.yml", "addons.parameters.yml", "vpc.yml"],
            ["appconfig-ipfilter.yml", "subscription-filter.yml"],
            False,
        ),
    ],
)
@freeze_time("2023-08-22 16:00:00")
@patch(
    "dbt_copilot_helper.utils.versioning.running_as_installed_package",
    new=Mock(return_value=False),
)
@patch("dbt_copilot_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
@patch(
    "dbt_copilot_helper.commands.copilot.get_log_destination_arn",
    new=Mock(
        return_value='{"prod": "arn:cwl_log_destination_prod", "dev": "arn:dev_cwl_log_destination"}'
    ),
)
@mock_s3
@mock_sts
@mock_iam
def test_pipeline_full_generate_creates_the_pipeline_configuration_and_addons(
    git_remote,
    get_aws_session_or_abort,
    fakefs,
    addon_file,
    expected_env_addons,
    expected_service_addons,
    expect_db_warning,
):
    mock_codestar_connections_boto_client(get_aws_session_or_abort, ["test-app"])
    setup_fixtures(fakefs)
    buildspec, cfn_patch, manifest = setup_output_file_paths_for_environments()

    addons_dir = FIXTURES_DIR / "make_addons"
    fakefs.add_real_directory(addons_dir / "config/copilot", read_only=False, target_path="copilot")
    fakefs.add_real_file(
        addons_dir / addon_file, read_only=False, target_path=ADDON_CONFIG_FILENAME
    )
    fakefs.add_real_directory(Path(addons_dir, "expected"), target_path="expected")

    result = CliRunner().invoke(generate)

    expected_files_dir = Path(EXPECTED_FILES_DIR) / "pipeline" / "pipelines"
    # Environments
    assert_yaml_in_output_file_matches_expected(
        buildspec, expected_files_dir / "environments" / "buildspec.yml"
    )
    assert_yaml_in_output_file_matches_expected(
        manifest, expected_files_dir / "environments" / "manifest.yml"
    )
    assert_yaml_in_output_file_matches_expected(
        cfn_patch, expected_files_dir / "environments" / "overrides/cfn.patches.yml"
    )
    assert_file_created_in_stdout(buildspec, result)
    assert_file_created_in_stdout(manifest, result)
    assert_file_created_in_stdout(cfn_patch, result)

    # Codebases
    output_files = setup_output_file_paths_for_codebases()
    assert_yaml_in_output_file_matches_expected(
        output_files[0], expected_files_dir / "application" / "manifest.yml"
    )

    for file in output_files:
        assert_file_created_in_stdout(file, result)

    ## Test that make_addons generates the expected directories and file contents

    assert (
        result.exit_code == 0
    ), f"The exit code should have been 0 (success) but was {result.exit_code}"
    db_warning = "Note: The key DATABASE_CREDENTIALS may need to be changed"
    assert (
        db_warning in result.stdout
    ) == expect_db_warning, "If we have a DB addon we expect a warning"

    expected_env_files = [Path("environments/addons", filename) for filename in expected_env_addons]
    expected_service_files = [Path("web/addons", filename) for filename in expected_service_addons]
    all_expected_files = expected_env_files + expected_service_files

    for f in all_expected_files:
        expected_file = Path("expected", f)

        if f.name == "vpc.yml":
            if addon_file == "rds_addons.yml":
                vpc_file = "rds-postgres"
            elif addon_file == "aurora_addons.yml":
                vpc_file = "aurora-postgres"
            else:
                vpc_file = "default"

            expected_file = Path(
                "expected/environments/addons",
                f"vpc-{vpc_file}.yml",
            )

        if f.name == "addons.parameters.yml" and addon_file in [
            "rds_addons.yml",
            "aurora_addons.yml",
        ]:
            expected_file = Path(
                "expected/environments/addons",
                "addons.parameters.rds.yml",
            )

        expected = expected_file.read_text()
        actual = Path("copilot", f).read_text()
        assert actual == expected, f"The file {f} did not have the expected content"

    env_override_files = setup_override_files_for_environments()
    for file in env_override_files:
        assert f"{file} created" in result.stdout
    all_expected_files += env_override_files

    expected_svc_overrides_file = Path("expected/web/overrides/cfn.patches.yml").read_text()
    actual_svc_overrides_file = Path("copilot/web/overrides/cfn.patches.yml").read_text()
    assert actual_svc_overrides_file == expected_svc_overrides_file

    copilot_dir = Path("copilot")
    actual_files = [
        Path(d, f).relative_to(copilot_dir) for d, _, files in os.walk(copilot_dir) for f in files
    ]

    assert (
        len(actual_files) == len(all_expected_files) + 3
    ), "The actual filecount should be expected files plus 2 initial manifest.yml and 1 override files"


def assert_yaml_in_output_file_matches_expected(output_file, expected_file):
    def get_yaml(content):
        return yaml.safe_load(content)

    actual_content = output_file.read_text()
    expected_content = expected_file.read_text()

    assert actual_content.partition("\n")[0].strip() == expected_content.partition("\n")[0].strip()
    assert get_yaml(actual_content) == get_yaml(expected_content)


def setup_output_file_paths_for_environments():
    output_dir = Path("./copilot/pipelines/environments")
    buildspec = output_dir / "buildspec.yml"
    manifest = output_dir / "manifest.yml"
    cfn_patch = output_dir / "overrides" / "cfn.patches.yml"
    return buildspec, cfn_patch, manifest


def setup_output_file_paths_for_codebases():
    output_dir = Path("copilot/pipelines/application")
    overrides_dir = output_dir / "overrides"

    return (
        output_dir / "manifest.yml",
        overrides_dir / "bin" / "override.ts",
        overrides_dir / ".gitignore",
        overrides_dir / "buildspec.deploy.yml",
        overrides_dir / "buildspec.image.yml",
        overrides_dir / "cdk.json",
        overrides_dir / "package-lock.json",
        overrides_dir / "package.json",
        overrides_dir / "stack.ts",
        overrides_dir / "tsconfig.json",
        overrides_dir / "types.ts",
    )


def setup_fixtures(fakefs):
    fakefs.add_real_file(FIXTURES_DIR / "valid_bootstrap_config.yml", False, "bootstrap.yml")
    fakefs.add_real_file(FIXTURES_DIR / "pipeline/pipelines.yml", False, "pipelines.yml")
    fakefs.add_real_file(FIXTURES_DIR / "valid_workspace.yml", False, "copilot/.workspace")
    fakefs.add_real_directory(EXPECTED_FILES_DIR / "pipeline" / "pipelines", True)


def setup_override_files_for_environments():
    overrides_dir = Path("./copilot/environments/overrides")
    return (
        overrides_dir / "bin" / "override.ts",
        overrides_dir / ".gitignore",
        overrides_dir / "cdk.json",
        overrides_dir / "log_resource_policy.json",
        overrides_dir / "package-lock.json",
        overrides_dir / "package.json",
        overrides_dir / "README.md",
        overrides_dir / "stack.ts",
        overrides_dir / "tsconfig.json",
    )
