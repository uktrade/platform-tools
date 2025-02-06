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


class VersionStatus:
    def __init__(
        self, local_version: SemanticVersion = None, latest_release: SemanticVersion = None
    ):
        self.local_version = local_version
        self.latest_release = latest_release
