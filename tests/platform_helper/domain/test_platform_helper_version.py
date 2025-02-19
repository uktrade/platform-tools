from unittest.mock import Mock
from unittest.mock import patch

from dbt_platform_helper.providers.semantic_version import PlatformHelperVersionStatus
from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)


@patch("click.secho")
@patch("dbt_platform_helper.utils.versioning.get_platform_helper_version_status")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
def test_check_platform_helper_version_needs_major_update_returns_red_warning_to_upgrade(
    mock_get_platform_helper_version_status, secho
):
    mock_get_platform_helper_version_status.return_value = PlatformHelperVersionStatus(
        local=SemanticVersion(1, 0, 0), latest=SemanticVersion(2, 0, 0)
    )

    check_platform_helper_version_needs_update()

    mock_get_platform_helper_version_status.assert_called_with(include_project_versions=False)

    secho.assert_called_with(
        "Error: You are running platform-helper v1.0.0, upgrade to v2.0.0 by running run `pip install "
        "--upgrade dbt-platform-helper`.",
        fg="red",
    )


@patch("click.secho")
@patch("dbt_platform_helper.utils.versioning.get_platform_helper_version_status")
@patch(
    "dbt_platform_helper.utils.versioning.running_as_installed_package", new=Mock(return_value=True)
)
def test_check_platform_helper_version_needs_minor_update_returns_warning_to_upgrade(
    mock_get_platform_helper_version_status, secho
):
    mock_get_platform_helper_version_status.return_value = PlatformHelperVersionStatus(
        SemanticVersion(1, 0, 0), SemanticVersion(1, 1, 0)
    )

    check_platform_helper_version_needs_update()

    mock_get_platform_helper_version_status.assert_called_with(include_project_versions=False)

    secho.assert_called_with(
        "You are running platform-helper v1.0.0, upgrade to v1.1.0 by running run `pip install "
        "--upgrade dbt-platform-helper`.",
        fg="magenta",
    )
