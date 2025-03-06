from unittest.mock import MagicMock
from unittest.mock import Mock

import pytest

from dbt_platform_helper.domain.config import Config
from dbt_platform_helper.domain.config import NoDeploymentRepoConfigException
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.semantic_version import PlatformHelperVersionStatus
from dbt_platform_helper.providers.semantic_version import SemanticVersion


class ConfigMocks:
    def __init__(self, *args, **kwargs):
        self.io = kwargs.get("io", Mock(spec=ClickIOProvider))
        self.platform_helper_versioning_domain = kwargs.get(
            "platform_helper_versioning_domain", MagicMock(spec=PlatformHelperVersioning)
        )
        self.platform_helper_versioning_domain._get_version_status.return_value = (
            PlatformHelperVersionStatus(SemanticVersion(1, 0, 0), SemanticVersion(1, 0, 0))
        )

    def params(self):
        return {
            "io": self.io,
            "platform_helper_versioning_domain": self.platform_helper_versioning_domain,
        }


class TestConfigValidate:

    def test_validate(self, fakefs):
        fakefs.create_file(
            "/copilot/environments/dev/addons/test_addon.yml",
            contents="# Generated by platform-helper v0.1.0",
        )

        config_mocks = ConfigMocks()
        config_domain = Config(**config_mocks.params())
        result = config_domain.validate()

        config_mocks.io.debug.assert_called_with("\nDetected a deployment repository\n")
        config_mocks.platform_helper_versioning_domain._get_version_status.assert_called_with(
            include_project_versions=True
        )

        assert result == PlatformHelperVersionStatus(
            SemanticVersion(1, 0, 0), SemanticVersion(1, 0, 0)
        )

    def test_no_repo(self, fakefs):
        config_domain = Config()
        with pytest.raises(
            NoDeploymentRepoConfigException,
            match="Could not find a deployment repository, no checks to run.",
        ):
            config_domain.validate()


class TestConfigGenerateAWS:
    pass
