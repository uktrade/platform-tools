import json
from unittest.mock import Mock
from unittest.mock import call
from unittest.mock import patch

import pytest
import yaml

from dbt_platform_helper.domain.cdn_detach import CDNDetach
from dbt_platform_helper.domain.terraform_environment import TerraformEnvironment
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.terraform import TerraformProvider
from tests.platform_helper.conftest import EXPECTED_DATA_DIR
from tests.platform_helper.conftest import INPUT_DATA_DIR


def create_mock_platform_config(alb_managed_ingress=True, s3_managed_ingress=True):
    return {
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
        "extensions": {
            "demodjango-alb": {
                "type": "alb",
                "environments": {
                    "staging": {
                        "managed_ingress": alb_managed_ingress,
                    },
                },
            },
            "demodjango-s3-bucket-static": {
                "type": "s3",
                "serve_static_content": True,
                "environments": {
                    "staging": {
                        "managed_ingress": s3_managed_ingress,
                    },
                },
            },
        },
    }


MOCK_RESOURCES_TO_DETACH = [
    {
        "module": 'module.extensions.module.cdn["demodjango-alb"]',
        "mode": "managed",
        "type": "aws_cloudfront_distribution",
        "name": "standard",
        "provider": 'module.extensions.provider["registry.terraform.io/hashicorp/aws"].domain-cdn',
        "instances": [
            {"index_key": "api.dev.demodjango.uktrade.digital"},
            {"index_key": "ip-filter-test.dev.demodjango.uktrade.digital"},
            {"index_key": "web.dev.demodjango.uktrade.digital"},
        ],
    },
    {
        "module": 'module.extensions.module.cdn["demodjango-alb"]',
        "mode": "managed",
        "type": "aws_cloudfront_cache_policy",
        "name": "cache_policy",
        "provider": 'module.extensions.provider["registry.terraform.io/hashicorp/aws"].domain-cdn',
        "instances": [{}],
    },
]


class CDNDetachMocks:
    def __init__(self, platform_config=create_mock_platform_config()):
        self.mock_io = Mock(spec=ClickIOProvider)
        self.mock_config_provider = Mock(spec=ConfigProvider)
        self.mock_config_provider.get_enriched_config.return_value = platform_config
        self.mock_terraform_environment = Mock(spec=TerraformEnvironment)
        self.mock_terraform_provider = Mock(spec=TerraformProvider)

    def params(self):
        return {
            "io": self.mock_io,
            "config_provider": self.mock_config_provider,
            "terraform_environment": self.mock_terraform_environment,
            "terraform_provider": self.mock_terraform_provider,
        }


class TestCDNDetach:
    @patch(
        "dbt_platform_helper.domain.cdn_detach.CDNDetach.get_resources_to_detach",
        return_value=MOCK_RESOURCES_TO_DETACH,
    )
    def test_dry_run_success(self, mock_get_resources_to_detach):
        mocks = CDNDetachMocks()
        cdn_detach = CDNDetach(**mocks.params())

        cdn_detach.execute(environment_name="staging", dry_run=True)

        mocks.mock_terraform_environment.generate.assert_called_once_with("staging")
        mocks.mock_terraform_provider.init.assert_called_once_with("terraform/environments/staging")
        mocks.mock_terraform_provider.pull_state.assert_called_once_with(
            "terraform/environments/staging"
        )
        mock_get_resources_to_detach.assert_called_once()

        mocks.mock_io.info.assert_has_calls(
            [
                call(
                    "Will remove the following resources from the staging environment's terraform state:"
                ),
                call(
                    '  module.extensions.module.cdn["demodjango-alb"].aws_cloudfront_cache_policy.cache_policy'
                ),
                call(
                    '  module.extensions.module.cdn["demodjango-alb"].aws_cloudfront_distribution.standard["api.dev.demodjango.uktrade.digital"]'
                ),
                call(
                    '  module.extensions.module.cdn["demodjango-alb"].aws_cloudfront_distribution.standard["ip-filter-test.dev.demodjango.uktrade.digital"]'
                ),
                call(
                    '  module.extensions.module.cdn["demodjango-alb"].aws_cloudfront_distribution.standard["web.dev.demodjango.uktrade.digital"]'
                ),
            ]
        )

    @patch(
        "dbt_platform_helper.domain.cdn_detach.CDNDetach.get_resources_to_detach",
        return_value=[],
    )
    def test_dry_run_success_with_no_resources_to_remove(self, mock_get_resources_to_detach):
        mocks = CDNDetachMocks()
        cdn_detach = CDNDetach(**mocks.params())

        cdn_detach.execute(environment_name="staging", dry_run=True)

        mocks.mock_terraform_environment.generate.assert_called_once_with("staging")
        mocks.mock_terraform_provider.init.assert_called_once_with("terraform/environments/staging")
        mocks.mock_terraform_provider.pull_state.assert_called_once_with(
            "terraform/environments/staging"
        )
        mock_get_resources_to_detach.assert_called_once()

        mocks.mock_io.info.assert_has_calls(
            [
                call(
                    "Will not remove any resources from the staging environment's terraform state."
                ),
            ]
        )

    @patch("dbt_platform_helper.domain.cdn_detach.CDNDetach.get_resources_to_detach", spec=True)
    def test_real_run_not_implemented(self, mock_get_resources_to_detach):
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

    @pytest.mark.parametrize(
        "platform_config,expected_data_filename",
        [
            (
                create_mock_platform_config(alb_managed_ingress=True, s3_managed_ingress=False),
                "alb.yaml",
            ),
            (
                create_mock_platform_config(alb_managed_ingress=False, s3_managed_ingress=True),
                "s3.yaml",
            ),
            (
                create_mock_platform_config(alb_managed_ingress=True, s3_managed_ingress=True),
                "alb_and_s3.yaml",
            ),
        ],
        ids=["alb", "s3", "alb+s3"],
    )
    def test_get_resources_to_detach(self, platform_config, expected_data_filename):
        with open(INPUT_DATA_DIR / "cdn_detach/terraform_state/typical.tfstate.json") as f:
            mock_terraform_state = json.load(f)
        with open(
            EXPECTED_DATA_DIR / "cdn_detach/resource_addrs_to_detach" / expected_data_filename
        ) as f:
            expected_resource_addrs = set(yaml.safe_load(f))

        mocks = CDNDetachMocks(platform_config)
        cdn_detach = CDNDetach(**mocks.params())

        resources = cdn_detach.get_resources_to_detach(mock_terraform_state, "staging")
        resource_addrs = {r["module"] + "." + r["type"] + "." + r["name"] for r in resources}

        assert resource_addrs == expected_resource_addrs
