import re
from pathlib import Path
from unittest.mock import patch

import yaml
from click.testing import CliRunner

from dbt_platform_helper.commands.version import get_platform_helper_for_project
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE


@patch("dbt_platform_helper.commands.version.get_required_platform_helper_version")
def test_calls_versioning_function_and_prints_returned_version(
    mock_get_required_platform_helper_version,
    fakefs,
    valid_platform_config,
):
    fakefs.create_file(Path(PLATFORM_CONFIG_FILE), contents=yaml.dump(valid_platform_config))
    mock_get_required_platform_helper_version.return_value = "1.2.3"

    result = CliRunner().invoke(get_platform_helper_for_project, [])

    assert len(mock_get_required_platform_helper_version.mock_calls) == 1
    assert mock_get_required_platform_helper_version.mock_calls[0].args == (None,)
    assert result.exit_code == 0
    assert re.match(r"\s*1\.2\.3\s*", result.output)


@patch("dbt_platform_helper.commands.version.get_required_platform_helper_version")
def test_calls_versioning_function_and_prints_returned_version_with_pipeline_override(
    mock_get_required_platform_helper_version,
    fakefs,
    valid_platform_config,
):
    fakefs.create_file(Path(PLATFORM_CONFIG_FILE), contents=yaml.dump(valid_platform_config))
    mock_get_required_platform_helper_version.return_value = "1.2.3"

    result = CliRunner().invoke(get_platform_helper_for_project, ["--pipeline", "main"])

    assert len(mock_get_required_platform_helper_version.mock_calls) == 1
    assert mock_get_required_platform_helper_version.mock_calls[0].args == ("main",)
    assert result.exit_code == 0
    assert re.match(r"\s*1\.2\.3\s*", result.output)


def test_works_with_with_incompatible_config_version(
    fakefs,
    invalid_platform_config_with_platform_version_overrides,
):
    fakefs.create_file(
        Path(PLATFORM_CONFIG_FILE),
        contents=yaml.dump(invalid_platform_config_with_platform_version_overrides),
    )

    result = CliRunner().invoke(get_platform_helper_for_project, [])

    assert result.exit_code == 0
    assert result.output == "1.2.3\n"


def test_fail_if_pipeline_option_is_not_a_pipeline(
    fakefs,
    valid_platform_config,
):
    fakefs.create_file(Path(PLATFORM_CONFIG_FILE), contents=yaml.dump(valid_platform_config))

    result = CliRunner().invoke(get_platform_helper_for_project, ["--pipeline", "bogus"])

    assert result.exit_code != 0
    assert "'bogus' is not one of" in result.output
    assert "'main'" in result.output
