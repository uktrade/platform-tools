from unittest.mock import Mock

from dbt_platform_helper.domain.cdn_detach import CDNDetach
from dbt_platform_helper.domain.terraform_environment import TerraformEnvironment
from dbt_platform_helper.providers.terraform_state import TerraformStateProvider


class CDNDetachMocks:
    def __init__(self):
        self.mock_terraform_environment = Mock(spec=TerraformEnvironment)
        self.mock_terraform_state_provider = Mock(spec=TerraformStateProvider)

    def params(self):
        return {
            "terraform_environment": self.mock_terraform_environment,
            "terraform_state_provider": self.mock_terraform_state_provider,
        }


class TestCDNDetach:
    def test_success(self):
        environment_name = "test"

        mocks = CDNDetachMocks()

        cdn_detach = CDNDetach(**mocks.params())
        cdn_detach.execute(environment_name)

        mocks.mock_terraform_environment.generate.assert_called_once_with(environment_name)
        mocks.mock_terraform_state_provider.pull.assert_called_once_with(
            f"terraform/environments/{environment_name}"
        )
