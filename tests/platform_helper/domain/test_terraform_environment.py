from unittest.mock import Mock

import pytest

from dbt_platform_helper.domain.terraform_environment import (
    PlatformTerraformManifestGenerator,
)
from dbt_platform_helper.domain.terraform_environment import TerraformEnvironment
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.files import FileProvider


class TestGenerateTerraform:

    # TODO this should live in config provider, then it can be mocked in these tests
    def test_get_enriched_config_returns_expected_config(self):
        mock_file_provider = Mock(spec=FileProvider)
        mock_file_provider.load.return_value = {
            "application": "test-app",
            "environments": {
                "*": {
                    "vpc": "vpc3",
                    "accounts": {
                        "deploy": {"name": "non-prod-acc", "id": "1122334455"},
                        "dns": {"name": "non-prod-dns-acc", "id": "6677889900"},
                    },
                },
                "test": {"versions": {"terraform-platform-modules": "123456"}},
            },
        }

        expected_enriched_config_config = {
            "application": "test-app",
            "environments": {
                "test": {
                    "vpc": "vpc3",
                    "accounts": {
                        "deploy": {"name": "non-prod-acc", "id": "1122334455"},
                        "dns": {"name": "non-prod-dns-acc", "id": "6677889900"},
                    },
                    "versions": {"terraform-platform-modules": "123456"},
                }
            },
        }

        mock_config_validator = Mock()

        result = TerraformEnvironment(
            ConfigProvider(mock_config_validator, mock_file_provider)
        ).get_enriched_config()
        assert result == expected_enriched_config_config

    # @patch("dbt_platform_helper.jinja2_tags.version", new=Mock(return_value="v0.1-TEST"))
    # @patch("dbt_platform_helper.providers.file.Fileprovider", new=Mock())
    # Test covers different versioning scenarios, ensuring cli correctly overrides config version
    @pytest.mark.skip()
    def test_terraform_environment_generate_writes_the_expected_manifest_to_file(
        self,
    ):

        mock_generator = PlatformTerraformManifestGenerator(Mock(spec=FileProvider))

        mock_config_provider = Mock(spec=ConfigProvider)
        mock_config_provider.load_and_validate_platform_config.return_value = {
            "application": "test-app",
            "environments": {
                "*": {
                    "vpc": "vpc3",
                    "accounts": {
                        "deploy": {"name": "non-prod-acc", "id": "1122334455"},
                        "dns": {"name": "non-prod-dns-acc", "id": "6677889900"},
                    },
                },
                "test": {"versions": {"terraform-platform-modules": 123456}},
            },
        }

        expected_test_environment_config = {
            "vpc": "vpc3",
            "accounts": {
                "deploy": {"name": "non-prod-acc", "id": "1122334455"},
                "dns": {"name": "non-prod-dns-acc", "id": "6677889900"},
            },
            "versions": {"terraform-platform-modules": 123456},
        }

        TerraformEnvironment(mock_config_provider).generate("test")

        mock_generator.generate_manifest.assert_called_once_with(
            "test-app", "test", expected_test_environment_config
        )
