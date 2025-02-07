import re
from typing import Union

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
