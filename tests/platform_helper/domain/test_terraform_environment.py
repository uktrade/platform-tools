from unittest.mock import Mock

import pytest

from dbt_platform_helper.domain.terraform_environment import TerraformEnvironment
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.environment_variable import (
    EnvironmentVariableProvider,
)
from dbt_platform_helper.providers.terraform_manifest import TerraformManifestProvider

VALID_ENV_CONFIG = {
    "vpc": "vpc3",
    "accounts": {
        "deploy": {"name": "non-prod-acc", "id": "1122334455"},
        "dns": {"name": "non-prod-dns-acc", "id": "6677889900"},
    },
}

VALID_ENRICHED_CONFIG = {
    "application": "test-app",
    "default_versions": {"platform-helper": "14.0.0"},
    "environments": {"test": VALID_ENV_CONFIG},
}

INVALID_ENRICHED_CONFIG = {
    "application": "test-app",
    "environments": {"test": VALID_ENV_CONFIG},
}


class GenerateTerraformMocks:
    def __init__(self):
        self.mock_config_provider = Mock(spec=ConfigProvider)
        self.mock_config_provider.get_enriched_config.return_value = VALID_ENRICHED_CONFIG
        self.mock_manifest_provider = Mock(spec=TerraformManifestProvider)
        self.mock_platform_helper_version_override = None
        self.mock_environment_variable_provider = Mock(spec=EnvironmentVariableProvider)

    def params(self):
        return {
            "config_provider": self.mock_config_provider,
            "manifest_provider": self.mock_manifest_provider,
            "platform_helper_version_override": self.mock_platform_helper_version_override,
            "environment_variable_provider": self.mock_environment_variable_provider,
        }


class TestGenerateTerraform:
    def test_raises_a_platform_exception_if_environment_does_not_exist_in_config(self):
        mocks = GenerateTerraformMocks()
        terraform_environment = TerraformEnvironment(**mocks.params())

        with pytest.raises(
            PlatformException,
            match="cannot generate terraform for environment not-an-environment.  It does not exist in your configuration",
        ):
            terraform_environment.generate("not-an-environment")

    @pytest.mark.parametrize(
        "use_environment_variable_platform_helper_version, expected_platform_helper_version, environment_terraform_module_path",
        [(False, "14.0.0", None), (True, "test-branch", "../local/path/")],
    )
    def test_generate_success(
        self,
        use_environment_variable_platform_helper_version,
        expected_platform_helper_version,
        environment_terraform_module_path,
    ):
        mocks = GenerateTerraformMocks()
        environment_name = "test"

        if use_environment_variable_platform_helper_version:
            mocks.mock_platform_helper_version_override = "test-branch"

        mocks.mock_environment_variable_provider.get_optional_value.return_value = (
            environment_terraform_module_path
        )

        terraform_environment = TerraformEnvironment(**mocks.params())

        terraform_environment.generate(environment_name)

        mocks.mock_manifest_provider.generate_environment_config.assert_called_once_with(
            VALID_ENRICHED_CONFIG,
            environment_name,
            expected_platform_helper_version,
            environment_terraform_module_path,
        )
