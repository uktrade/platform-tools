from unittest.mock import Mock
from unittest.mock import patch

import yaml

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_FILE
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.providers.semantic_version import SemanticVersion


class TestPlatformHelperVersioningGetStatus:
    # TODO clean up mocking
    @patch("requests.get")
    def test_get_platform_helper_version_status_given_config_and_deprecated_version_file(
        self, mock_get, fakefs, valid_platform_config
    ):
        mock_local_version = Mock()
        mock_local_version.get_installed_tool_version.return_value = SemanticVersion(1, 1, 1)

        mock_get.return_value.json.return_value = {
            "releases": {"1.2.3": None, "2.3.4": None, "0.1.0": None}
        }
        fakefs.create_file(PLATFORM_HELPER_VERSION_FILE, contents="5.6.7")
        config = valid_platform_config
        fakefs.create_file(PLATFORM_CONFIG_FILE, contents=yaml.dump(config))

        version_status = PlatformHelperVersioning(
            local_version_provider=mock_local_version
        ).get_version_status()

        assert version_status.local == SemanticVersion(1, 1, 1)
        assert version_status.latest == SemanticVersion(2, 3, 4)
        assert version_status.deprecated_version_file == SemanticVersion(5, 6, 7)
        assert version_status.platform_config_default == SemanticVersion(10, 2, 0)
        assert version_status.pipeline_overrides == {"test": "main", "prod-main": "9.0.9"}

    @patch("requests.get")
    def test_get_platform_helper_version_status_with_invalid_yaml_in_platform_config(
        self, mock_latest_release_request, fakefs
    ):
        mock_local_version = Mock()
        mock_local_version.get_installed_tool_version.return_value = SemanticVersion(1, 1, 1)

        mock_latest_release_request.return_value.json.return_value = {
            "releases": {"1.2.3": None, "2.3.4": None, "0.1.0": None}
        }
        fakefs.create_file(PLATFORM_HELPER_VERSION_FILE, contents="5.6.7")
        fakefs.create_file(PLATFORM_CONFIG_FILE, contents="{")

        version_status = PlatformHelperVersioning(
            local_version_provider=mock_local_version
        ).get_version_status()

        assert version_status.local == SemanticVersion(1, 1, 1)
        assert version_status.latest == SemanticVersion(2, 3, 4)
        assert version_status.deprecated_version_file == SemanticVersion(5, 6, 7)
        assert version_status.platform_config_default == None
        assert version_status.pipeline_overrides == {}

    @patch("requests.get")
    def test_get_platform_helper_version_status_with_invalid_config(
        self,
        mock_get,
        fakefs,
        create_invalid_platform_config_file,
    ):

        mock_local_version = Mock()
        mock_local_version.get_installed_tool_version.return_value = SemanticVersion(1, 1, 1)

        mock_get.return_value.json.return_value = {
            "releases": {"1.2.3": None, "2.3.4": None, "0.1.0": None}
        }
        fakefs.create_file(PLATFORM_HELPER_VERSION_FILE, contents="5.6.7")

        version_status = PlatformHelperVersioning(
            local_version_provider=mock_local_version
        ).get_version_status()

        assert version_status.local == SemanticVersion(1, 1, 1)
        assert version_status.latest == SemanticVersion(2, 3, 4)
        assert version_status.deprecated_version_file == SemanticVersion(5, 6, 7)
        assert version_status.platform_config_default == SemanticVersion(1, 2, 3)
        assert version_status.pipeline_overrides == {"prod-main": "9.0.9"}
