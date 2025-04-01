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
        migrated_config = deepcopy(platform_config)

        self._remove_terraform_platform_modules_default_version(migrated_config)
        self._remove_terraform_platform_modules_from_env_config(migrated_config)
        self._remove_to_account_and_from_account_from_database_copy(migrated_config)

        return migrated_config

    def _remove_terraform_platform_modules_from_env_config(self, migrated_config: dict) -> None:
        for env in migrated_config.get("environments", {}).values():
            if env and "versions" in env:
                del env["versions"]

    def _remove_terraform_platform_modules_default_version(self, migrated_config: dict) -> None:
        if "default_versions" in migrated_config:
            default_versions = migrated_config["default_versions"]
            if "terraform-platform-modules" in default_versions:
                del default_versions["terraform-platform-modules"]

    def _remove_to_account_and_from_account_from_database_copy(self, migrated_config: dict) -> None:
        for extension in migrated_config.get("extensions", {}).values():
            if extension.get("type") == "postgres" and "database_copy" in extension:
                for database_copy_block in extension["database_copy"]:
                    if "from_account" in database_copy_block:
                        del database_copy_block["from_account"]
                    if "to_account" in database_copy_block:
                        del database_copy_block["to_account"]


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
