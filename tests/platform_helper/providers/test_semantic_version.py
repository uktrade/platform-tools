import pytest

from dbt_platform_helper.providers.semantic_version import (
    IncompatibleMajorVersionException,
)
from dbt_platform_helper.providers.semantic_version import (
    IncompatibleMinorVersionException,
)
from dbt_platform_helper.providers.semantic_version import PlatformHelperVersionStatus
from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.semantic_version import VersionStatus


class TestSemanticVersion:
    @pytest.mark.parametrize(
        "suite",
        [
            (SemanticVersion(1, 2, 3), "1.2.3"),
            (SemanticVersion(0, 1, -1), "0.1.-1"),
            (SemanticVersion(-1, 0, 2), "-1.0.2"),
            (SemanticVersion(None, None, None), "unknown"),
        ],
    )
    def test_stringify_version_numbers(self, suite):
        input_version, expected_version = suite
        assert str(input_version) == expected_version

    def test_same_semantic_versions_are_equal(self):
        assert SemanticVersion(1, 2, 3) == SemanticVersion(1, 2, 3)

    def test_different_semantic_versions_are_not_equal(self):
        assert SemanticVersion(1, 1, 1) != SemanticVersion(1, 2, 3)

    @pytest.mark.parametrize(
        "version_check",
        [
            (
                SemanticVersion(1, 40, 0),
                SemanticVersion(1, 30, 0),
                IncompatibleMinorVersionException,
            ),
            (
                SemanticVersion(1, 40, 0),
                SemanticVersion(2, 1, 0),
                IncompatibleMajorVersionException,
            ),
            (
                SemanticVersion(0, 2, 40),
                SemanticVersion(0, 1, 30),
                IncompatibleMajorVersionException,
            ),
            (
                SemanticVersion(0, 1, 40),
                SemanticVersion(0, 1, 30),
                IncompatibleMajorVersionException,
            ),
        ],
    )
    def test_validate_compatability_with(self, version_check):
        app_version, check_version, raises = version_check

        with pytest.raises(raises):
            app_version.validate_compatibility_with(check_version)

    @pytest.mark.parametrize(
        "suite",
        [
            ("v1.2.3", SemanticVersion(1, 2, 3)),
            ("1.2.3", SemanticVersion(1, 2, 3)),
            ("v0.1-TEST", SemanticVersion(0, 1, -1)),
            ("TEST-0.2", SemanticVersion(-1, 0, 2)),
            ("unknown", None),
            (None, None),
        ],
    )
    def test_from_string(self, suite):
        input_version, expected_version = suite
        result = SemanticVersion.from_string(input_version)
        assert result == expected_version


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
            {
                "main": SemanticVersion(2, 0, 0),
                "dev": SemanticVersion(2, 1, 1),
            },
        )
        result = f"{platform_helper_version_status}"
        assert (
            result
            == "PlatformHelperVersionStatus: installed: 1.2.0, latest: 1.2.3, deprecated_version_file: 1.1.1, platform_config_default: 1.0.0, pipeline_overrides: main: 2.0.0, dev: 2.1.1"
        )

    def test_to_string_with_no_pipeline_overrides(self):
        platform_helper_version_status = PlatformHelperVersionStatus(
            SemanticVersion(1, 2, 0),
            SemanticVersion(1, 2, 3),
            SemanticVersion(1, 1, 1),
            SemanticVersion(1, 0, 0),
        )
        result = f"{platform_helper_version_status}"
        assert (
            result
            == "PlatformHelperVersionStatus: installed: 1.2.0, latest: 1.2.3, deprecated_version_file: 1.1.1, platform_config_default: 1.0.0"
        )
