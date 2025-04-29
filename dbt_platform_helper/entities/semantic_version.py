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
    def __init__(self, major: int, minor: int, patch: int):
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
        if other is None:
            return False
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def validate_compatibility_with(self, other):
        if other is None:
            raise ValidationException("Cannot compare NoneType")
        if (self.major == 0 and other.major == 0) and (
            self.minor != other.minor or self.patch != other.patch
        ):
            raise IncompatibleMajorVersionException(str(self), str(other))

        if self.major != other.major:
            raise IncompatibleMajorVersionException(str(self), str(other))

        if self.minor != other.minor:
            raise IncompatibleMinorVersionException(str(self), str(other))

    @staticmethod
    def _cast_to_int_with_fallback(input, fallback=-1):
        try:
            return int(input)
        except ValueError:
            return fallback

    @classmethod
    def from_string(self, version_string: Union[str, None]):
        if version_string is None:
            return None

        version_segments = re.split(r"[.\-]", version_string.replace("v", ""))

        if len(version_segments) != 3:
            return None

        major, minor, patch = [self._cast_to_int_with_fallback(s) for s in version_segments]

        return SemanticVersion(major, minor, patch)

    @staticmethod
    def is_semantic_version(version_string):
        valid_semantic_string_regex = r"(?i)^v?[0-9]+[.-][0-9]+[.-][0-9]+$"
        return re.match(valid_semantic_string_regex, version_string)
