import pytest
from click.testing import CliRunner

from dbt_platform_helper.commands.config import validate


@pytest.mark.xdist_group(name="fileaccess")
def test_running_in_non_copilot_directory():
    result = CliRunner().invoke(validate)
    assert result.output == "Could not find a deployment repository, no checks to run.\n"


def test_with_outdated_addons_templates(fakefs, mock_tool_versions):
    get_app_versions, get_aws_versions, get_copilot_versions = mock_tool_versions
    get_app_versions.return_value = (1, 0, 0), (1, 0, 0)
    get_aws_versions.return_value = (1, 0, 0), (1, 0, 0)
    get_copilot_versions.return_value = (1, 0, 0), (1, 0, 0)

    fakefs.create_file(
        "/copilot/environments/dev/addons/test_addon.yml",
        contents="# Generated by platform-helper v0.1.0",
    )

    result = CliRunner().invoke(validate)

    assert "Detected a deployment repository" in result.output
    assert "Checking tooling versions..." in result.output
    assert (
        "| aws                |     1.0.0     |      1.0.0       |        ✔        |"
    ) in result.output
    assert (
        "| copilot            |     1.0.0     |      1.0.0       |        ✔        |"
    ) in result.output
    assert (
        "| dbt-platform-tools |     1.0.0     |      1.0.0       |        ✔        |"
    ) in result.output

    assert (
        "| copilot/environments/dev/addons/test_addon.yml |     0.1.0      |           ✖       "
        "     |            ✖            |"
    ) in result.output


def test_with_outdated_platform_helper(fakefs, mock_tool_versions):
    get_app_versions, get_aws_versions, get_copilot_versions = mock_tool_versions
    get_app_versions.return_value = (0, 1, 0), (1, 0, 0)
    get_aws_versions.return_value = (1, 0, 0), (1, 0, 0)
    get_copilot_versions.return_value = (1, 0, 0), (1, 0, 0)

    fakefs.create_file(
        "/copilot/environments/dev/addons/test_addon.yml",
        contents="# Generated by platform-helper v1.0.0",
    )

    result = CliRunner().invoke(validate)

    assert "Detected a deployment repository" in result.output
    assert "Checking tooling versions..." in result.output
    assert (
        "| aws                |     1.0.0     |      1.0.0       |        ✔        |"
    ) in result.output
    assert (
        "| copilot            |     1.0.0     |      1.0.0       |        ✔        |"
    ) in result.output
    assert (
        "| dbt-platform-tools |     0.1.0     |      1.0.0       |        ✖        |"
    ) in result.output

    assert (
        "| copilot/environments/dev/addons/test_addon.yml |     1.0.0      |           ✖      "
        "      |            ✔            |"
    ) in result.output


def test_with_outdated_tools(fakefs, mock_tool_versions):
    get_app_versions, get_aws_versions, get_copilot_versions = mock_tool_versions
    get_app_versions.return_value = (0, 1, 0), (1, 0, 0)
    get_aws_versions.return_value = (0, 1, 0), (1, 0, 0)
    get_copilot_versions.return_value = (0, 1, 0), (1, 0, 0)

    fakefs.create_file(
        "/copilot/environments/dev/addons/test_addon.yml",
        contents="# Generated by platform-helper v1.0.0",
    )

    result = CliRunner().invoke(validate)
    assert (
        """
Recommendations:

  - Upgrade AWS CLI to version 1.0.0.
  - Upgrade AWS Copilot to version 1.0.0.
  - Upgrade dbt-platform-tools to version 1.0.0 `pip install --upgrade dbt-platform-tools==1.0.0`.
    Post upgrade, run `platform-helper copilot make-addons` to update your addon templates.
"""
        in result.output
    )
