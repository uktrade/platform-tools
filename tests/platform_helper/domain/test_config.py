import pytest

from dbt_platform_helper.domain.config import Config
from dbt_platform_helper.domain.config import NoDeploymentRepoConfigException


class TestConfigValidate:
    def test_validate(self):

        config_domain = Config()
        result = config_domain.validate()
        assert result

    def test_no_repo(self, fakefs):
        config_domain = Config()
        with pytest.raises(
            NoDeploymentRepoConfigException,
            match="Could not find a deployment repository, no checks to run.",
        ):
            config_domain.validate()


class TestConfigGenerateAWS:
    pass
