import os

from dbt_platform_helper.platform_exception import PlatformException


class EnvironmentVariableProvider:
    def __init__(self):
        pass

    def get_value(self, env_var: str) -> str:
        """Returns the value or raises a PlatformException if not set or
        empty."""
        value = os.environ.get(env_var)
        if not value:
            raise PlatformException(f"Environment variable '{env_var}' is not set or is empty")
        return value

    def get_optional_value(self, env_var: str) -> str | None:
        """Returns the value or None if not set."""
        return os.environ.get(env_var)
