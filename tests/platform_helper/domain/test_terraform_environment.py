from unittest.mock import Mock

import pytest

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
            manifest_provider=Mock(),
            io=Mock(),
        )
        with pytest.raises(
            PlatformException,
            match="cannot generate terraform for environment not-an-environment.  It does not exist in your configuration",
        ):
            terraform_environment.generate("not-an-environment")
