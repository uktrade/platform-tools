from collections import Counter
from collections import OrderedDict
from copy import deepcopy
from typing import Protocol

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.schema_migrations.schema_v0_to_v1_migration import (
    SchemaV0ToV1Migration,
)
from dbt_platform_helper.providers.version import InstalledVersionProvider


class InvalidMigrationConfigurationException(PlatformException):
    pass


class SchemaMigrationProtocol(Protocol):
    def from_version(self) -> int: ...

    def migrate(self, platform_config: dict) -> dict: ...


# TODO: Possibly get this programmatically?
ALL_MIGRATIONS = [SchemaV0ToV1Migration()]


class Migrator:
    def __init__(
        self,
        migrations: list[SchemaMigrationProtocol],
        installed_version_provider: InstalledVersionProvider = InstalledVersionProvider,
        io_provider: ClickIOProvider = ClickIOProvider(),
    ):
        self.migrations = sorted(migrations, key=lambda m: m.from_version())
        self.installed_version_provider = installed_version_provider
        self.io_provider = io_provider
        from_version_counts = Counter([migration.from_version() for migration in self.migrations])
        duplicate_from_versions = [count for count in from_version_counts.values() if count > 1]

        if duplicate_from_versions:
            raise InvalidMigrationConfigurationException(
                "`from_version` parameters must be unique amongst migrations"
            )

    def migrate(self, platform_config: dict) -> dict:
        out = OrderedDict(deepcopy(platform_config))
        if "schema_version" not in out:
            out["schema_version"] = 0

        if "default_versions" in out:
            out.move_to_end("default_versions", last=False)
        if "schema_version" in out:
            out.move_to_end("schema_version", last=False)
        if "application" in out:
            out.move_to_end("application", last=False)

        for migration in self.migrations:
            migration_can_be_applied = migration.from_version() == out["schema_version"]
            if migration_can_be_applied:
                out = migration.migrate(out)
                schema_version = out["schema_version"]
                self.io_provider.info(
                    f"Migrating from platform config schema version {schema_version} to version {schema_version + 1}"
                )
                out["schema_version"] += 1

        if "default_versions" not in out:
            out["default_versions"] = {}

        out["default_versions"]["platform-helper"] = str(
            self.installed_version_provider.get_semantic_version("dbt-platform-helper")
        )

        self.io_provider.info("\nMigration complete")

        return dict(out)
