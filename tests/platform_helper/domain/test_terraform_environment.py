from unittest.mock import Mock

import pytest

from dbt_platform_helper.domain.terraform_environment import (
    PlatformTerraformManifestGenerator,
)
from dbt_platform_helper.domain.terraform_environment import TerraformEnvironment
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider


class TestGenerateTerraform:

    VALID_ENV_CONFIG = {
        "vpc": "vpc3",
        "accounts": {
            "deploy": {"name": "non-prod-acc", "id": "1122334455"},
            "dns": {"name": "non-prod-dns-acc", "id": "6677889900"},
        },
        "versions": {"terraform-platform-modules": "123456"},
    }

    VALID_ENRICHED_CONFIG = {
        "application": "test-app",
        "environments": {"test": VALID_ENV_CONFIG},
    }

    def test_raises_a_platform_exception_if_environment_does_not_exist_in_config(self):
        mock_config_provider = Mock(spec=ConfigProvider)
        mock_config_provider.get_enriched_config.return_value = self.VALID_ENRICHED_CONFIG

        terraform_environment = TerraformEnvironment(
            config_provider=mock_config_provider,
            manifest_generator=Mock(),
            echo_fn=Mock(),
        )
        with pytest.raises(
            PlatformException,
            match="Error: cannot generate terraform for environment not-an-environment.  It does not exist in your configuration",
        ):
            terraform_environment.generate("not-an-environment")

    # TODO test can be made more complete by using a file fixture for the expected content on the manifest
    # (See copilot tests)
    def test_terraform_environment_generate_writes_the_expected_manifest_to_file(
        self,
    ):
        mock_config_provider = Mock(spec=ConfigProvider)
        mock_config_provider.get_enriched_config.return_value = self.VALID_ENRICHED_CONFIG

        mock_generator = Mock(spec=PlatformTerraformManifestGenerator)
        mock_generator.generate_manifest.return_value = "I am a junk manifest for testing!"
        mock_generator.write_manifest.return_value = "Hello, World!"

        mock_echo_fn = Mock()

        terraform_environment = TerraformEnvironment(
            config_provider=mock_config_provider,
            manifest_generator=mock_generator,
            echo_fn=mock_echo_fn,
        )

        terraform_environment.generate("test")

        mock_generator.generate_manifest.assert_called_with(
            environment_name="test",
            application_name="test-app",
            environment_config=self.VALID_ENV_CONFIG,
            terraform_platform_modules_version_override=None,
        )
        mock_generator.write_manifest.assert_called_with(
            environment_name="test", manifest_content="I am a junk manifest for testing!"
        )
        mock_echo_fn.assert_called_with("Hello, World!")
