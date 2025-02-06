import pytest

from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.validation import IncompatibleMajorVersionException
from dbt_platform_helper.providers.validation import IncompatibleMinorVersionException


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
    def test_validate_version_compatability(self, version_check):
        app_version, check_version, raises = version_check

        with pytest.raises(raises):
            app_version.validate_version_compatibility(check_version)
