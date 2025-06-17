import os

import pytest

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.environment_variable import (
    EnvironmentVariableProvider,
)


class TestEnvironmentVariableProvider:
    def setup_method(self):
        self.provider = EnvironmentVariableProvider()
        self.env_var = "TEST_ENV_VAR"

    # Unset self.env_var after each test. Avoid KeyError by setting None as default when self.env_var is not set.
    def teardown_method(self):
        os.environ.pop(self.env_var, None)

    def test_get_value_returns_value_when_set(self):
        os.environ[self.env_var] = " some-value "
        assert self.provider.get_required(self.env_var) == "some-value"

    def test_get_value_raises_exception_when_not_set(self):
        with pytest.raises(PlatformException):
            self.provider.get_required(self.env_var)

    def test_get_value_raises_exception_when_empty(self):
        os.environ[self.env_var] = ""
        with pytest.raises(PlatformException):
            self.provider.get_required(self.env_var)

    def test_get_optional_value_returns_value_when_set(self):
        os.environ[self.env_var] = " optional-value "
        assert self.provider.get(self.env_var) == "optional-value"

    def test_get_optional_value_returns_none_when_not_set(self):
        assert self.provider.get(self.env_var) is None

    def test_get_value_raises_exception_when_whitespace_only(self):
        os.environ[self.env_var] = "   "
        with pytest.raises(PlatformException):
            self.provider.get_required(self.env_var)

    def test_get_optional_value_returns_none_when_whitespace_only(self):
        os.environ[self.env_var] = "   "
        assert self.provider.get(self.env_var) is None
