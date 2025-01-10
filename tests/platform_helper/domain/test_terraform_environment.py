from unittest.mock import Mock

from dbt_platform_helper.domain.terraform_environment import (
    PlatformTerraformManifestGenerator,
)
from dbt_platform_helper.domain.terraform_environment import TerraformEnvironment
from dbt_platform_helper.providers.config import ConfigProvider


class TestGenerateTerraform:

    def test_terraform_environment_generate_writes_the_expected_manifest_to_file(
        self,
    ):

        mock_generator = Mock(spec=PlatformTerraformManifestGenerator)

        test_environment_config = {
            "vpc": "vpc3",
            "accounts": {
                "deploy": {"name": "non-prod-acc", "id": "1122334455"},
                "dns": {"name": "non-prod-dns-acc", "id": "6677889900"},
            },
            "versions": {"terraform-platform-modules": 123456},
        }

        enriched_config = {
            "application": "test-app",
            "environments": {"test": test_environment_config},
        }

        mock_config_provider = Mock(spec=ConfigProvider)
        mock_echo_fn = Mock()
        mock_config_provider.get_enriched_config.return_value = enriched_config
        mock_generator.generate_manifest.return_value = "I am a junk manifest for testing!"
        mock_generator.write_manifest.return_value = "Hello, World!"

        terraform_environment = TerraformEnvironment(
            config_provider=mock_config_provider,
            manifest_generator=mock_generator,
            echo_fn=mock_echo_fn,
        )

        terraform_environment.generate("test")

        mock_generator.generate_manifest.assert_called_with(
            environment_name="test",
            application_name="test-app",
            environment_config=test_environment_config,
            terraform_platform_modules_version_override=None,
        )
        mock_generator.write_manifest.assert_called_with(
            environment_name="test", manifest_content="I am a junk manifest for testing!"
        )
        mock_echo_fn.assert_called_with("Hello, World!")
