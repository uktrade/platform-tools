from unittest.mock import Mock
from unittest.mock import patch

from dbt_platform_helper.domain.platform_helper_version import PlatformHelperVersion
from dbt_platform_helper.providers.semantic_version import SemanticVersion


@patch("dbt_platform_helper.domain.platform_helper_version.version")
@patch(
    "dbt_platform_helper.domain.platform_helper_version.running_as_installed_package",
    new=Mock(return_value=True),
)
def test_check_platform_helper_version_needs_major_update_returns_red_warning_to_upgrade(
    mock_local_version,
):
    mock_local_version.return_value = "1.0.0"
    mock_pypi_provider = Mock()
    mock_pypi_provider.get_latest_version.return_value = SemanticVersion(2, 0, 0)
    mock_io_provider = Mock()

    PlatformHelperVersion(
        io=mock_io_provider, pypi_provider=mock_pypi_provider
    ).check_if_needs_update()

    mock_io_provider.error.assert_called_with(
        "You are running platform-helper v1.0.0, upgrade to v2.0.0 by running run `pip install "
        "--upgrade dbt-platform-helper`."
    )


@patch("dbt_platform_helper.domain.platform_helper_version.version")
@patch(
    "dbt_platform_helper.domain.platform_helper_version.running_as_installed_package",
    new=Mock(return_value=True),
)
def test_check_platform_helper_version_needs_minor_update_returns_warning_to_upgrade(
    mock_local_version,
):
    mock_local_version.return_value = "1.0.0"
    mock_pypi_provider = Mock()
    mock_pypi_provider.get_latest_version.return_value = SemanticVersion(1, 1, 0)
    mock_io_provider = Mock()

    PlatformHelperVersion(
        io=mock_io_provider, pypi_provider=mock_pypi_provider
    ).check_if_needs_update()

    mock_io_provider.warn.assert_called_with(
        "You are running platform-helper v1.0.0, upgrade to v1.1.0 by running run `pip install "
        "--upgrade dbt-platform-helper`."
    )
