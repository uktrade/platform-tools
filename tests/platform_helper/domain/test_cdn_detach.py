import json
from unittest.mock import Mock
from unittest.mock import call

import pytest
import yaml

from dbt_platform_helper.domain.cdn_detach import CDNDetach
from dbt_platform_helper.domain.cdn_detach import CDNDetachLogic
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


MOCK_RESOURCE_BLOCKS_TO_DETACH = [
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
    def __init__(self, **mock_logic_result_attrs):
        self.mock_io = Mock(spec=ClickIOProvider)
        self.mock_config_provider = Mock(spec=ConfigProvider)
        self.mock_config_provider.get_enriched_config.return_value = create_mock_platform_config()
        self.mock_terraform_environment = Mock(spec=TerraformEnvironment)
        self.mock_terraform_provider = Mock(spec=TerraformProvider)
        self.mock_logic_constructor = Mock(return_value=Mock(**mock_logic_result_attrs))

    def params(self):
        return {
            "io": self.mock_io,
            "config_provider": self.mock_config_provider,
            "terraform_environment": self.mock_terraform_environment,
            "terraform_provider": self.mock_terraform_provider,
            "logic_constructor": self.mock_logic_constructor,
        }


class TestCDNDetach:
    def test_dry_run_success(self):
        mocks = CDNDetachMocks(
            resource_blocks_to_detach=MOCK_RESOURCE_BLOCKS_TO_DETACH,
        )

        cdn_detach = CDNDetach(**mocks.params())
        cdn_detach.execute(environment_name="staging", dry_run=True)

        mocks.mock_terraform_environment.generate.assert_called_once_with("staging")
        mocks.mock_terraform_provider.init.assert_called_once_with("terraform/environments/staging")
        mocks.mock_terraform_provider.pull_state.assert_called_once_with(
            "terraform/environments/staging"
        )
        mocks.mock_logic_constructor.assert_called_once()

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

    def test_dry_run_success_with_no_resources_to_detach(self):
        mocks = CDNDetachMocks(
            resource_blocks_to_detach=[],
        )

        cdn_detach = CDNDetach(**mocks.params())
        cdn_detach.execute(environment_name="staging", dry_run=True)

        mocks.mock_io.info.assert_has_calls(
            [
                call(
                    "Will not remove any resources from the staging environment's terraform state."
                ),
            ]
        )

    def test_real_run_not_implemented(self):
        mocks = CDNDetachMocks(
            resource_blocks_to_detach=MOCK_RESOURCE_BLOCKS_TO_DETACH,
        )

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


class TestCDNDetachLogic:
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
    def test_resource_blocks_to_detach(self, platform_config, expected_data_filename):
        with open(INPUT_DATA_DIR / "cdn_detach/terraform_state/typical.tfstate.json") as f:
            environment_tfstate = json.load(f)
        with open(
            EXPECTED_DATA_DIR / "cdn_detach/resource_addrs_to_detach" / expected_data_filename
        ) as f:
            expected_resource_addrs = set(yaml.safe_load(f))

        logic_result = CDNDetachLogic(
            platform_config=platform_config,
            environment_name="staging",
            environment_tfstate=environment_tfstate,
        )

        resource_addrs = {
            rb["module"] + "." + rb["type"] + "." + rb["name"]
            for rb in logic_result.resource_blocks_to_detach
        }
        assert resource_addrs == expected_resource_addrs
