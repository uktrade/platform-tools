import pytest
import re
import yaml

from pathlib import Path
from unittest.mock import patch
from click.testing import CliRunner

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE


@pytest.fixture
def get_platform_helper_for_project_with_valid_config(fakefs, valid_platform_config):
    fakefs.create_file(Path(PLATFORM_CONFIG_FILE), contents=yaml.dump(valid_platform_config))
    from dbt_platform_helper.commands.version import get_platform_helper_for_project

    return get_platform_helper_for_project


@pytest.fixture
def get_platform_helper_for_project_with_invalid_config(
    fakefs, invalid_platform_config_with_platform_version_overrides
):
    fakefs.create_file(
        Path(PLATFORM_CONFIG_FILE),
        contents=yaml.dump(invalid_platform_config_with_platform_version_overrides),
    )
    from dbt_platform_helper.commands.version import get_platform_helper_for_project

    return get_platform_helper_for_project


@patch("dbt_platform_helper.commands.version.get_required_platform_helper_version")
def test_calls_versioning_function_and_prints_returned_version(
    mock_get_required_platform_helper_version,
):
    mock_get_required_platform_helper_version.return_value = "1.2.3"

    from dbt_platform_helper.commands.version import get_platform_helper_for_project

    result = CliRunner().invoke(get_platform_helper_for_project, [])

    assert len(mock_get_required_platform_helper_version.mock_calls) == 1
    assert mock_get_required_platform_helper_version.mock_calls[0].args == (None,)
    assert result.exit_code == 0
    assert re.match(r"\s*1\.2\.3\s*", result.output)


@patch("dbt_platform_helper.commands.version.get_required_platform_helper_version")
def test_calls_versioning_function_and_prints_returned_version_with_pipeline_override(
    mock_get_required_platform_helper_version,
):
    mock_get_required_platform_helper_version.return_value = "1.2.3"

    from dbt_platform_helper.commands.version import get_platform_helper_for_project

    result = CliRunner().invoke(get_platform_helper_for_project, ["--pipeline", "main"])

    assert len(mock_get_required_platform_helper_version.mock_calls) == 1
    assert mock_get_required_platform_helper_version.mock_calls[0].args == ("main",)
    assert result.exit_code == 0
    assert re.match(r"\s*1\.2\.3\s*", result.output)


def test_works_with_invalid_config_with_pipeline_override(
    get_platform_helper_for_project_with_invalid_config,
):
    result = CliRunner().invoke(
        get_platform_helper_for_project_with_invalid_config, ["--pipeline", "prod-main"]
    )

    assert result.exit_code == 0
    assert result.output == "9.0.9\n"


def test_works_with_with_incompatible_config_version(
    get_platform_helper_for_project_with_invalid_config,
):

    result = CliRunner().invoke(get_platform_helper_for_project_with_invalid_config, [])

    assert result.exit_code == 0
    assert result.output == "1.2.3\n"


def test_fail_if_pipeline_option_is_not_a_pipeline(
    get_platform_helper_for_project_with_valid_config,
):
    result = CliRunner().invoke(
        get_platform_helper_for_project_with_valid_config, ["--pipeline", "bogus"]
    )

    assert result.exit_code != 0
    assert "'bogus' is not one of" in result.output
    assert "'main'" in result.output


def test_still_fails_if_pipeline_option_is_not_a_pipeline_with_invalid_config(
    get_platform_helper_for_project_with_invalid_config,
):
    result = CliRunner().invoke(
        get_platform_helper_for_project_with_invalid_config, ["--pipeline", "bogus"]
    )

    assert result.exit_code != 0
    assert "'bogus' is not " in result.output
    assert "'prod-main'" in result.output


def test_pipeline_override_with_invalid_config(
    get_platform_helper_for_project_with_invalid_config,
):
    result = CliRunner().invoke(
        get_platform_helper_for_project_with_invalid_config, ["--pipeline", "prod-main"]
    )

    assert result.exit_code == 0
    assert result.output == "9.0.9\n"
