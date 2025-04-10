import pytest

from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.version_status import PlatformHelperVersionStatus
from dbt_platform_helper.providers.version_status import VersionStatus


class TestVersionStatus:
    @pytest.mark.parametrize(
        "suite",
        [
            (SemanticVersion(1, 2, 3), SemanticVersion(1, 2, 3), False),
            (SemanticVersion(1, 2, 0), SemanticVersion(1, 2, 3), True),
        ],
    )
    def test_is_outdated(self, suite):
        local_version, latest_release, expected = suite
        assert (
            VersionStatus(installed=local_version, latest=latest_release).is_outdated() == expected
        )

    def test_to_string(self):
        result = f"{VersionStatus(SemanticVersion(1, 2, 0), SemanticVersion(1, 2, 3))}"
        assert result == "VersionStatus: installed: 1.2.0, latest: 1.2.3"


class TestPlatformHelperVersionStatus:
    def test_to_string_with_populated_attributes(self):
        platform_helper_version_status = PlatformHelperVersionStatus(
            SemanticVersion(1, 2, 0),
            SemanticVersion(1, 2, 3),
            SemanticVersion(1, 1, 1),
            SemanticVersion(1, 0, 0),
            SemanticVersion(2, 0, 0),
            {
                "main": SemanticVersion(2, 0, 0),
                "dev": SemanticVersion(2, 1, 1),
            },
        )
        result = f"{platform_helper_version_status}"
        assert (
            result
            == "PlatformHelperVersionStatus: installed: 1.2.0, latest: 1.2.3, deprecated_version_file: 1.1.1, platform_config_default: 1.0.0, cli_override: 2.0.0, pipeline_overrides: main: 2.0.0, dev: 2.1.1"
        )

    def test_to_string_with_no_pipeline_overrides(self):
        platform_helper_version_status = PlatformHelperVersionStatus(
            SemanticVersion(1, 2, 0),
            SemanticVersion(1, 2, 3),
            SemanticVersion(1, 1, 1),
            SemanticVersion(1, 0, 0),
            SemanticVersion(2, 0, 0),
        )
        result = f"{platform_helper_version_status}"
        assert (
            result
            == "PlatformHelperVersionStatus: installed: 1.2.0, latest: 1.2.3, deprecated_version_file: 1.1.1, platform_config_default: 1.0.0, cli_override: 2.0.0"
        )
