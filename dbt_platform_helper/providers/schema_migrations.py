from collections import Counter
from copy import deepcopy
from typing import Protocol

from dbt_platform_helper.platform_exception import PlatformException


class InvalidMigrationConfigurationException(PlatformException):
    pass


class SchemaMigrationProtocol(Protocol):
    def from_version(self) -> int: ...

    def migrate(self, platform_config: dict) -> dict: ...


class SchemaV1ToV2Migration:
    def from_version(self) -> int:
        return 1

    def migrate(self, platform_config: dict) -> dict:
        output = deepcopy(platform_config)

        if "default_versions" in output:
            default_versions = output["default_versions"]
            if "terraform-platform-modules" in default_versions:
                del default_versions["terraform-platform-modules"]

        return output


ALL_MIGRATIONS = [SchemaV1ToV2Migration()]


class Migrator:
    def __init__(self, *migrations: SchemaMigrationProtocol):
        self.migrations = sorted(migrations, key=lambda m: m.from_version())
        from_version_counts = Counter([migration.from_version() for migration in self.migrations])
        duplicate_from_versions = [count for count in from_version_counts.values() if count > 1]

        if duplicate_from_versions:
            raise InvalidMigrationConfigurationException(
                "`from_version` parameters must be unique amongst migrations"
            )

    def migrate(self, platform_config: dict) -> dict:
        out = deepcopy(platform_config)
        if "schema_version" not in out:
            out["schema_version"] = 1

        for migration in self.migrations:
            if migration.from_version() != out["schema_version"]:
                continue
            out = migration.migrate(out)
            out["schema_version"] += 1

        return out
