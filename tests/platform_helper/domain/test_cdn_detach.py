import json
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import yaml

from dbt_platform_helper.domain.cdn_detach import CDNDetach
from dbt_platform_helper.domain.terraform_environment import TerraformEnvironment
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.terraform import TerraformProvider
from tests.platform_helper.conftest import EXPECTED_DATA_DIR
from tests.platform_helper.conftest import INPUT_DATA_DIR

MOCK_ENRICHED_CONFIG = {
    "application": "test-app",
    "default_versions": {"platform-helper": "14.0.0"},
    "environments": {
        "staging": {
            "vpc": "vpc3",
            "accounts": {
                "deploy": {"name": "non-prod-acc", "id": "1122334455"},
                "dns": {"name": "non-prod-dns-acc", "id": "6677889900"},
            },
        },
    },
}


class CDNDetachMocks:
    def __init__(self):
        self.mock_config_provider = Mock(spec=ConfigProvider)
        self.mock_config_provider.get_enriched_config.return_value = MOCK_ENRICHED_CONFIG
        self.mock_terraform_environment = Mock(spec=TerraformEnvironment)
        self.mock_terraform_provider = Mock(spec=TerraformProvider)

    def params(self):
        return {
            "config_provider": self.mock_config_provider,
            "terraform_environment": self.mock_terraform_environment,
            "terraform_provider": self.mock_terraform_provider,
        }


class TestCDNDetach:
    @patch("dbt_platform_helper.domain.cdn_detach.CDNDetach.filter_resources_to_detach", spec=True)
    def test_dry_run_success(self, mock_filter):
        mocks = CDNDetachMocks()
        cdn_detach = CDNDetach(**mocks.params())

        cdn_detach.execute(environment_name="staging", dry_run=True)

        mocks.mock_terraform_environment.generate.assert_called_once_with("staging")
        mocks.mock_terraform_provider.init.assert_called_once_with("terraform/environments/staging")
        mocks.mock_terraform_provider.pull_state.assert_called_once_with(
            "terraform/environments/staging"
        )
        mock_filter.assert_called_once()

    @patch("dbt_platform_helper.domain.cdn_detach.CDNDetach.filter_resources_to_detach", spec=True)
    def test_real_run_not_implemented(self, mock_filter):
        mocks = CDNDetachMocks()
        cdn_detach = CDNDetach(**mocks.params())

        with pytest.raises(NotImplementedError):
            cdn_detach.execute(environment_name="staging", dry_run=False)

    def test_exception_raised_if_env_not_in_config(self):
        mocks = CDNDetachMocks()
        cdn_detach = CDNDetach(**mocks.params())

        with pytest.raises(
            PlatformException,
            match="cannot detach CDN resources for environment not-an-environment. It does not exist in your configuration",
        ):
            cdn_detach.execute(environment_name="not-an-environment", dry_run=True)

    def test_filter_resources_to_detach(self):
        with open(INPUT_DATA_DIR / "cdn_detach/terraform_state/typical.tfstate.json") as f:
            mock_terraform_state = json.load(f)
        with open(EXPECTED_DATA_DIR / "cdn_detach/filtered_resources/typical.yaml") as f:
            expected_resource_addrs = {
                (x["module"], x["mode"], x["type"], x["name"]) for x in yaml.safe_load(f)
            }

        mocks = CDNDetachMocks()
        cdn_detach = CDNDetach(**mocks.params())

        resources = cdn_detach.filter_resources_to_detach(mock_terraform_state)
        resource_addrs = {(r["module"], r["mode"], r["type"], r["name"]) for r in resources}

        assert resource_addrs == expected_resource_addrs
