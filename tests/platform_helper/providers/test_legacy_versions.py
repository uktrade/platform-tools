from unittest.mock import Mock

import yaml

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.legacy_versions import LegacyVersionsProvider


def test_check_terraform_platform_modules_version_detects_tpm_versions_in_cli(
    fakefs,
    platform_config_for_env_pipelines,
):
    """Test that, given a CLI entry for terraform-platform-modules version or a
    platform config object that contains deprecated terraform-platform-modules
    versions, will raise a warning."""

    mock_io = Mock()
    fakefs.create_file(
        PLATFORM_CONFIG_FILE,
        contents=yaml.dump(platform_config_for_env_pipelines),
    )

    config_object = ConfigProvider().load_and_validate_platform_config()

    LegacyVersionsProvider(mock_io).check_terraform_platform_modules_version("7.0.0", config_object)

    mock_io.warn.assert_called_once_with(
        "The `--terraform-platform-modules-version` flag for the pipeline generate command is deprecated. "
        "Please use the `--platform-helper-version` flag instead.\n"
    )


def test_check_terraform_platform_modules_version_detects_tpm_versions_in_platform_config(
    fakefs,
    platform_config_for_env_pipelines_with_deprecated_tpm_default_versions,
):
    """Test that, given a platform config object that contains deprecated
    terraform-platform-modules in default_versions, will raise a warning."""

    mock_io = Mock()
    fakefs.create_file(
        PLATFORM_CONFIG_FILE,
        contents=yaml.dump(platform_config_for_env_pipelines_with_deprecated_tpm_default_versions),
    )

    config_object = ConfigProvider().load_and_validate_platform_config()

    LegacyVersionsProvider(mock_io).check_terraform_platform_modules_version(None, config_object)

    mock_io.warn.assert_called_once_with(
        "The `terraform-platform-modules` key set in the platform-config.yml file in the following location: `default_versions: terraform-platform-modules` is now deprecated. "
        "Please use the `default_versions: platform-helper` value instead. "
        "See full platform config reference in the docs: "
        "https://platform.readme.trade.gov.uk/reference/platform-config-yml/#core-configuration.\n"
    )


def test_check_terraform_platform_modules_version_detects_tpm_versions_in_config_environments_versions(
    fakefs,
    platform_config_for_env_pipelines,
):
    """Test that, given a platform config object that contains deprecated
    terraform-platform-modules in environments/<env>/versions, will raise a
    warning."""

    mock_io = Mock()
    fakefs.create_file(
        PLATFORM_CONFIG_FILE,
        contents=yaml.dump(platform_config_for_env_pipelines),
    )

    config_object = ConfigProvider().load_and_validate_platform_config()
    config_object["environments"]["dev"]["versions"] = {"terraform-platform-modules": "12.0.0"}

    LegacyVersionsProvider(mock_io).check_terraform_platform_modules_version(None, config_object)

    mock_io.warn.assert_called_once_with(
        "The `terraform-platform-modules` key set in the platform-config.yml file in the following location:  `environments: <env>: versions: terraform-platform-modules` is now deprecated. "
        "Please use the `default_versions: platform-helper` value instead. "
        "See full platform config reference in the docs: "
        "https://platform.readme.trade.gov.uk/reference/platform-config-yml/#core-configuration.\n"
    )
