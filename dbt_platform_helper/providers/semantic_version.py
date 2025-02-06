from dbt_platform_helper.providers.validation import IncompatibleMajorVersionException
from dbt_platform_helper.providers.validation import IncompatibleMinorVersionException


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

    def validate_version_compatibility(self, other):
        app_major, app_minor, app_patch = self.major, self.minor, self.patch
        check_major, check_minor, check_patch = (
            other.major,
            other.minor,
            other.patch,
        )
        app_version_as_string = str(self)
        check_version_as_string = str(other)

        if (app_major == 0 and check_major == 0) and (
            app_minor != check_minor or app_patch != check_patch
        ):
            raise IncompatibleMajorVersionException(app_version_as_string, check_version_as_string)

        if app_major != check_major:
            raise IncompatibleMajorVersionException(app_version_as_string, check_version_as_string)

        if app_minor != check_minor:
            raise IncompatibleMinorVersionException(app_version_as_string, check_version_as_string)


class VersionStatus:
    def __init__(
        self, local_version: SemanticVersion = None, latest_release: SemanticVersion = None
    ):
        self.local_version = local_version
        self.latest_release = latest_release
