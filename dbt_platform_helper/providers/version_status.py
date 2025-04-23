from dataclasses import dataclass

from dbt_platform_helper.entities.semantic_version import SemanticVersion
from dbt_platform_helper.platform_exception import PlatformException


class UnsupportedVersionException(PlatformException):
    def __init__(self, version: str):
        super().__init__(
            f"""Platform-helper version {version} is not compatible with platform-helper. Please install version platform-helper version 14 or later."""
        )


@dataclass
class VersionStatus:
    installed: SemanticVersion = None
    latest: SemanticVersion = None

    def __str__(self):
        attrs = {
            key: value for key, value in vars(self).items() if isinstance(value, SemanticVersion)
        }
        attrs_str = ", ".join(f"{key}: {value}" for key, value in attrs.items())
        return f"{self.__class__.__name__}: {attrs_str}"

    def is_outdated(self):
        return self.installed != self.latest
