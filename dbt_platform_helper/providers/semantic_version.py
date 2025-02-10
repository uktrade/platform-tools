import re
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


class VersionStatus:
    def __init__(
        self, local_version: SemanticVersion = None, latest_release: SemanticVersion = None
    ):
        self.local = local_version
        self.latest = latest_release

    def is_outdated(self):
        return self.local != self.latest

    def warn(self):
        pass


class PlatformHelperVersionStatus(VersionStatus):
    def __init__(
        self,
        local: SemanticVersion = None,
        latest: SemanticVersion = None,
        deprecated_version_file: SemanticVersion = None,
        platform_config_default: SemanticVersion = None,
        pipeline_overrides: dict[str, str] = None,
    ):
        self.local = local
        self.latest = latest
        self.deprecated_version_file = deprecated_version_file
        self.platform_config_default = platform_config_default
        self.pipeline_overrides = pipeline_overrides if pipeline_overrides else {}

    def warn(self) -> dict:
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
            message += f"{missing_default_version_message}{self.local}\n"
            errors.append(message)

        return {
            "warnings": warnings,
            "errors": errors,
        }
