import os

import pytest

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.environment_variable import (
    EnvironmentVariableProvider,
)


class TestEnvironmentVariableProvider:

    env_var = "TEST_ENV_VAR"

    # Unset self.env_var after each test
    def teardown_method(self):
        del os.environ[self.env_var]

    @pytest.mark.parametrize(
        "value, expected_value",
        [
            (" some-value ", "some-value"),
            ("optional-value", "optional-value"),
        ],
    )
    @pytest.mark.parametrize(
        "method", [EnvironmentVariableProvider.get, EnvironmentVariableProvider.get_required]
    )
    def test_valid_values_return_stripped_values(self, method, value, expected_value):
        os.environ[self.env_var] = value
        assert method(self.env_var) == expected_value

    @pytest.mark.parametrize("value", ["", "   ", " \n "])
    def test_get_required_raises_exception_on_invalid_values(self, value):
        os.environ[self.env_var] = value
        with pytest.raises(PlatformException):
            EnvironmentVariableProvider.get_required(self.env_var)

    @pytest.mark.parametrize("value", ["", "   "])
    def test_get_returns_none_on_invalid_values(self, value):
        os.environ[self.env_var] = value
        assert EnvironmentVariableProvider.get(self.env_var) is None
