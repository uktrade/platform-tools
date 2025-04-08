from unittest.mock import Mock

import pytest

from dbt_platform_helper.domain.terraform_environment import TerraformEnvironment
from dbt_platform_helper.domain.versioning import PlatformHelperVersionNotFoundException
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.terraform_manifest import TerraformManifestProvider


class TestGenerateTerraform:

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

    def test_raises_a_platform_exception_if_environment_does_not_exist_in_config(self):
        mock_config_provider = Mock(spec=ConfigProvider)
        mock_config_provider.get_enriched_config.return_value = self.VALID_ENRICHED_CONFIG

        terraform_environment = TerraformEnvironment(
            config_provider=mock_config_provider,
            manifest_provider=Mock(),
            io=Mock(),
        )
        with pytest.raises(
            PlatformException,
            match="cannot generate terraform for environment not-an-environment.  It does not exist in your configuration",
        ):
            terraform_environment.generate("not-an-environment")

    def test_terraform_environment_raises_a_platform_helper_version_not_found_exception_if_default_versions_is_empty_in_config(
        self,
    ):
        mock_config_provider = Mock(spec=ConfigProvider)
        mock_config_provider.get_enriched_config.return_value = self.INVALID_ENRICHED_CONFIG

        terraform_environment = TerraformEnvironment(
            config_provider=mock_config_provider,
            manifest_provider=Mock(),
            io=Mock(),
        )
        with pytest.raises(
            PlatformHelperVersionNotFoundException,
            match="cannot find 'platform-helper' in 'default_versions' in the platform-config.yml file.",
        ):
            terraform_environment.generate("test")

    def test_generate_success(self):
        environment_name = "test"
        platform_helper_version = "14.0.0"

        mock_manifest_provider = Mock(spec=TerraformManifestProvider)

        mock_config_provider = Mock(spec=ConfigProvider)
        mock_config_provider.get_enriched_config.return_value = self.VALID_ENRICHED_CONFIG

        terraform_environment = TerraformEnvironment(
            config_provider=mock_config_provider,
            manifest_provider=mock_manifest_provider,
            io=Mock(),
        )

        terraform_environment.generate(environment_name)

        mock_manifest_provider.generate_environment_config.assert_called_once_with(
            self.VALID_ENRICHED_CONFIG, environment_name, platform_helper_version
        )
