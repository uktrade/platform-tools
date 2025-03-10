import re
from dataclasses import dataclass
from dataclasses import field
from typing import Dict
from typing import Optional
from typing import Union

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_FILE
from dbt_platform_helper.providers.validation import ValidationException


class IncompatibleMajorVersionException(ValidationException):
    def __init__(self, app_version: str, check_version: str):
        super().__init__()
        self.app_version = app_version
        self.check_version = check_version


class IncompatibleMinorVersionException(ValidationException):
    def __init__(self, app_version: str, check_version: str):
        super().__init__()
        self.app_version = app_version
        self.check_version = check_version


class SemanticVersion:
    def __init__(self, major, minor, patch):
        self.major = major
        self.minor = minor
        self.patch = patch

    def __str__(self) -> str:
        if self.major is None:
            return "unknown"
        return ".".join([str(s) for s in [self.major, self.minor, self.patch]])

    def __repr__(self) -> str:
        return str(self)

    def __lt__(self, other) -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __eq__(self, other) -> bool:
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def validate_compatibility_with(self, other):
        if (self.major == 0 and other.major == 0) and (
            self.minor != other.minor or self.patch != other.patch
        ):
            raise IncompatibleMajorVersionException(str(self), str(other))

        if self.major != other.major:
            raise IncompatibleMajorVersionException(str(self), str(other))

        if self.minor != other.minor:
            raise IncompatibleMinorVersionException(str(self), str(other))

    @staticmethod
    def from_string(version_string: Union[str, None]):
        if version_string is None:
            return None

        version_plain = version_string.replace("v", "")
        version_segments = re.split(r"[.\-]", version_plain)

        if len(version_segments) != 3:
            return None

        output_version = [0, 0, 0]
        for index, segment in enumerate(version_segments):
            try:
                output_version[index] = int(segment)
            except ValueError:
                output_version[index] = -1

        return SemanticVersion(output_version[0], output_version[1], output_version[2])


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

    def validate(self):
        pass


@dataclass
class PlatformHelperVersionStatus(VersionStatus):
    installed: Optional[SemanticVersion] = None
    latest: Optional[SemanticVersion] = None
    deprecated_version_file: Optional[SemanticVersion] = None
    platform_config_default: Optional[SemanticVersion] = None
    pipeline_overrides: Optional[Dict[str, str]] = field(default_factory=dict)

    def __str__(self):
        semantic_version_attrs = {
            key: value for key, value in vars(self).items() if isinstance(value, SemanticVersion)
        }

        class_str = ", ".join(f"{key}: {value}" for key, value in semantic_version_attrs.items())

        if self.pipeline_overrides.items():
            pipeline_overrides_str = "pipeline_overrides: " + ", ".join(
                f"{key}: {value}" for key, value in self.pipeline_overrides.items()
            )
            class_str = ", ".join([class_str, pipeline_overrides_str])

        return f"{self.__class__.__name__}: {class_str}"

    def validate(self) -> dict:
        if self.platform_config_default and not self.deprecated_version_file:
            return {}

        warnings = []
        errors = []

        missing_default_version_message = f"Create a section in the root of '{PLATFORM_CONFIG_FILE}':\n\ndefault_versions:\n  platform-helper: "
        deprecation_message = (
            f"Please delete '{PLATFORM_HELPER_VERSION_FILE}' as it is now deprecated."
        )

        if self.platform_config_default and self.deprecated_version_file:
            warnings.append(deprecation_message)

        if not self.platform_config_default and self.deprecated_version_file:
            warnings.append(deprecation_message)
            warnings.append(f"{missing_default_version_message}{self.deprecated_version_file}\n")

        if not self.platform_config_default and not self.deprecated_version_file:
            message = f"Cannot get dbt-platform-helper version from '{PLATFORM_CONFIG_FILE}'.\n"
            message += f"{missing_default_version_message}{self.installed}\n"
            errors.append(message)

        return {
            "warnings": warnings,
            "errors": errors,
        }
