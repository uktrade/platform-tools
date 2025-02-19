from unittest.mock import Mock
from unittest.mock import patch

from dbt_platform_helper.domain.platform_helper_version import PlatformHelperVersion
from dbt_platform_helper.providers.semantic_version import PlatformHelperVersionStatus
from dbt_platform_helper.providers.semantic_version import SemanticVersion


@patch("dbt_platform_helper.domain.platform_helper_version.get_platform_helper_version_status")
@patch(
    "dbt_platform_helper.domain.platform_helper_version.running_as_installed_package",
    new=Mock(return_value=True),
)
def test_check_platform_helper_version_needs_major_update_returns_red_warning_to_upgrade(
    mock_get_platform_helper_version_status,
):
    mock_get_platform_helper_version_status.return_value = PlatformHelperVersionStatus(
        local=SemanticVersion(1, 0, 0), latest=SemanticVersion(2, 0, 0)
    )

    mock_io_provider = Mock()
    PlatformHelperVersion(mock_io_provider).check_if_needs_update()

    mock_get_platform_helper_version_status.assert_called_with(include_project_versions=False)

    mock_io_provider.error.assert_called_with(
        "You are running platform-helper v1.0.0, upgrade to v2.0.0 by running run `pip install "
        "--upgrade dbt-platform-helper`."
    )


@patch("dbt_platform_helper.domain.platform_helper_version.get_platform_helper_version_status")
@patch(
    "dbt_platform_helper.domain.platform_helper_version.running_as_installed_package",
    new=Mock(return_value=True),
)
def test_check_platform_helper_version_needs_minor_update_returns_warning_to_upgrade(
    mock_get_platform_helper_version_status,
):
    mock_get_platform_helper_version_status.return_value = PlatformHelperVersionStatus(
        SemanticVersion(1, 0, 0), SemanticVersion(1, 1, 0)
    )

    mock_io_provider = Mock()

    PlatformHelperVersion(mock_io_provider).check_if_needs_update()

    mock_get_platform_helper_version_status.assert_called_with(include_project_versions=False)

    mock_io_provider.warn.assert_called_with(
        "You are running platform-helper v1.0.0, upgrade to v1.1.0 by running run `pip install "
        "--upgrade dbt-platform-helper`."
    )
