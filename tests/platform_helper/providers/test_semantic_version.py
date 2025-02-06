import pytest

from dbt_platform_helper.providers.semantic_version import SemanticVersion


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
