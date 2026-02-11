import json
from unittest.mock import Mock
from unittest.mock import call

import pytest
import yaml

from dbt_platform_helper.domain.cdn_detach import CDNDetach
from dbt_platform_helper.domain.cdn_detach import CDNDetachLogic
from dbt_platform_helper.domain.cdn_detach import CDNResourcesNotImportedException
from dbt_platform_helper.domain.cdn_detach import address_for_tfstate_resource
from dbt_platform_helper.domain.terraform_environment import TerraformEnvironment
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.terraform import TerraformProvider
from dbt_platform_helper.providers.terraform_manifest import TerraformManifestProvider
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
        "index_key": "api.dev.demodjango.uktrade.digital",
    },
    {
        "module": 'module.extensions.module.cdn["demodjango-alb"]',
        "mode": "managed",
        "type": "aws_cloudfront_distribution",
        "name": "standard",
        "provider": 'module.extensions.provider["registry.terraform.io/hashicorp/aws"].domain-cdn',
        "index_key": "ip-filter-test.dev.demodjango.uktrade.digital",
    },
    {
        "module": 'module.extensions.module.cdn["demodjango-alb"]',
        "mode": "managed",
        "type": "aws_cloudfront_distribution",
        "name": "standard",
        "provider": 'module.extensions.provider["registry.terraform.io/hashicorp/aws"].domain-cdn',
        "index_key": "web.dev.demodjango.uktrade.digital",
    },
    {
        "module": 'module.extensions.module.cdn["demodjango-alb"]',
        "mode": "managed",
        "type": "aws_cloudfront_cache_policy",
        "name": "cache_policy",
        "provider": 'module.extensions.provider["registry.terraform.io/hashicorp/aws"].domain-cdn',
    },
]


class CDNDetachMocks:
    def __init__(self, **mock_logic_result_attrs):
        self.mock_io = Mock(spec=ClickIOProvider)
        self.mock_config_provider = Mock(spec=ConfigProvider)
        self.mock_config_provider.get_enriched_config.return_value = create_mock_platform_config()
        self.mock_terraform_environment = Mock(spec=TerraformEnvironment)
        self.mock_manifest_provider = Mock(spec=TerraformManifestProvider)
        self.mock_terraform_provider = Mock(spec=TerraformProvider)
        self.mock_logic_constructor = Mock(return_value=Mock(**mock_logic_result_attrs))

    def params(self):
        return {
            "io": self.mock_io,
            "config_provider": self.mock_config_provider,
            "terraform_environment": self.mock_terraform_environment,
            "manifest_provider": self.mock_manifest_provider,
            "terraform_provider": self.mock_terraform_provider,
            "logic_constructor": self.mock_logic_constructor,
        }


class TestCDNDetach:
    def test_dry_run_success(self):
        mocks = CDNDetachMocks(
            resources_to_detach=MOCK_RESOURCES_TO_DETACH,
            resources_not_in_ingress_tfstate=[],
        )

        cdn_detach = CDNDetach(**mocks.params())
        cdn_detach.execute(environment_name="staging", dry_run=True)

        mocks.mock_terraform_environment.generate.assert_called_once_with("staging")
        mocks.mock_manifest_provider.generate_platform_public_ingress_config.assert_called_once_with(
            "test-app",
            "staging",
            "non-prod-dns-acc",
        )
        mocks.mock_terraform_provider.init.assert_has_calls(
            [
                call("terraform/environments/staging"),
                call("terraform/platform-public-ingress/test-app/staging"),
            ]
        )
        mocks.mock_terraform_provider.pull_state.assert_has_calls(
            [
                call("terraform/environments/staging"),
                call("terraform/platform-public-ingress/test-app/staging"),
            ]
        )

        mocks.mock_logic_constructor.assert_called_once()

        mocks.mock_io.info.assert_has_calls(
            [
                call("Fetching a copy of the staging environment's terraform state..."),
                call(
                    "Fetching a copy of the platform-public-ingress terraform state for test-app/staging..."
                ),
                call(""),
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
            resources_to_detach=[],
            resources_not_in_ingress_tfstate=[],
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

    def test_dry_run_failure_if_resources_missing_from_ingress_tfstate(self):
        mocks = CDNDetachMocks(
            resources_to_detach=MOCK_RESOURCES_TO_DETACH,
            resources_not_in_ingress_tfstate=MOCK_RESOURCES_TO_DETACH[:2],
        )

        cdn_detach = CDNDetach(**mocks.params())
        with pytest.raises(CDNResourcesNotImportedException) as e:
            cdn_detach.execute(environment_name="staging", dry_run=True)

        assert e.value.resources == MOCK_RESOURCES_TO_DETACH[:2]

    def test_real_run_not_implemented(self):
        mocks = CDNDetachMocks(
            resources_to_detach=MOCK_RESOURCES_TO_DETACH,
            resources_not_in_ingress_tfstate=[],
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


@pytest.fixture
def mock_environment_tfstate():
    with open(INPUT_DATA_DIR / "cdn_detach/terraform_state/environment.tfstate.json") as f:
        return json.load(f)


@pytest.fixture
def mock_ingress_tfstate():
    with open(INPUT_DATA_DIR / "cdn_detach/terraform_state/ingress.tfstate.json") as f:
        return json.load(f)


class TestCDNDetachLogic:
    @pytest.mark.parametrize(
        "platform_config,expected_data_filename",
        [
            (
                create_mock_platform_config(alb_managed_ingress=True, s3_managed_ingress=False),
                "to_detach.alb.yaml",
            ),
            (
                create_mock_platform_config(alb_managed_ingress=False, s3_managed_ingress=True),
                "to_detach.s3.yaml",
            ),
            (
                create_mock_platform_config(alb_managed_ingress=True, s3_managed_ingress=True),
                "to_detach.alb_and_s3.yaml",
            ),
        ],
        ids=["alb", "s3", "alb+s3"],
    )
    def test_resources_to_detach(
        self,
        mock_environment_tfstate,
        mock_ingress_tfstate,
        platform_config,
        expected_data_filename,
    ):
        with open(EXPECTED_DATA_DIR / "cdn_detach/resource_addrs" / expected_data_filename) as f:
            expected_resource_addrs = set(yaml.safe_load(f))

        logic_result = CDNDetachLogic(
            platform_config=platform_config,
            environment_name="staging",
            environment_tfstate=mock_environment_tfstate,
            ingress_tfstate=mock_ingress_tfstate,
        )

        resource_addrs = {address_for_tfstate_resource(r) for r in logic_result.resources_to_detach}
        assert resource_addrs == expected_resource_addrs

    def test_resources_not_in_ingress_tfstate(self, mock_environment_tfstate, mock_ingress_tfstate):
        with open(EXPECTED_DATA_DIR / "cdn_detach/resource_addrs/not_in_ingress_tfstate.yaml") as f:
            expected_resource_addrs = set(yaml.safe_load(f))

        logic_result = CDNDetachLogic(
            platform_config=create_mock_platform_config(),
            environment_name="staging",
            environment_tfstate=mock_environment_tfstate,
            ingress_tfstate=mock_ingress_tfstate,
        )

        resource_addrs = {
            address_for_tfstate_resource(r) for r in logic_result.resources_not_in_ingress_tfstate
        }
        assert resource_addrs == expected_resource_addrs


class TestAddressForTerraformResource:
    def test_no_index_key(self):
        resource = {
            "module": 'module.s3["my-ext"]',
            "mode": "managed",
            "type": "aws_s3_bucket_versioning",
            "name": "this-versioning",
        }

        address = address_for_tfstate_resource(resource)

        assert address == 'module.s3["my-ext"].aws_s3_bucket_versioning.this-versioning'

    def test_string_index_key(self):
        resource = {
            "module": 'module.s3["my-ext"]',
            "mode": "managed",
            "type": "aws_s3_object",
            "name": "object",
            "index_key": "test.html",
        }

        address = address_for_tfstate_resource(resource)

        assert address == 'module.s3["my-ext"].aws_s3_object.object["test.html"]'

    def test_integer_index_key(self):
        resource = {
            "module": 'module.s3["my-ext"]',
            "mode": "managed",
            "type": "aws_ssm_parameter",
            "name": "cloudfront_alias",
            "index_key": 0,
        }

        address = address_for_tfstate_resource(resource)

        assert address == 'module.s3["my-ext"].aws_ssm_parameter.cloudfront_alias[0]'
