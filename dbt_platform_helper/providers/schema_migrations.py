from collections import Counter
from collections import OrderedDict
from copy import deepcopy
from typing import Protocol

from dbt_platform_helper.platform_exception import PlatformException


class InvalidMigrationConfigurationException(PlatformException):
    pass


class PlatformConfigSchemaMigrationException(PlatformException):
    pass


class SchemaMigrationProtocol(Protocol):
    def from_version(self) -> int: ...

    def migrate(self, platform_config: dict) -> dict: ...

    def messages(self) -> list[str]: ...


class SchemaV0ToV1Migration:
    def __init__(self):
        self._messages = []

    def from_version(self) -> int:
        return 0

    def migrate(self, platform_config: dict) -> dict:
        migrated_config = deepcopy(platform_config)

        self._remove_terraform_platform_modules_default_version(migrated_config)
        self._remove_versions_from_env_config(migrated_config)
        self._remove_to_account_and_from_account_from_database_copy(migrated_config)

        return migrated_config

    def messages(self):
        return self._messages

    def _remove_versions_from_env_config(self, migrated_config: dict) -> None:
        for env_name, env in migrated_config.get("environments", {}).items():
            if env and "versions" in env:
                del env["versions"]
                self._messages.append(
                    f"environments.{env_name}.versions is deprecated and no longer used. Please delete from your platform-config.yml"
                )

    def _remove_terraform_platform_modules_default_version(self, migrated_config: dict) -> None:
        if "default_versions" in migrated_config:
            default_versions = migrated_config["default_versions"]
            if "terraform-platform-modules" in default_versions:
                del default_versions["terraform-platform-modules"]
                self._messages.append(
                    "default_versions.terraform-platform-modules is deprecated and no longer used. Please delete from your platform-config.yml"
                )

    def _remove_to_account_and_from_account_from_database_copy(self, migrated_config: dict) -> None:
        for extension_name, extension in migrated_config.get("extensions", {}).items():
            if extension.get("type") == "postgres" and "database_copy" in extension:
                for database_copy_block in extension["database_copy"]:
                    if "from_account" in database_copy_block:
                        del database_copy_block["from_account"]
                        self._messages.append(
                            f"extensions.{extension_name}.database_copy.from_account is deprecated and no longer used. Please delete from your platform-config.yml",
                        )
                    if "to_account" in database_copy_block:
                        del database_copy_block["to_account"]
                        self._messages.append(
                            f"extensions.{extension_name}.database_copy.to_account is deprecated and no longer used. Please delete from your platform-config.yml",
                        )


ALL_MIGRATIONS = [SchemaV0ToV1Migration()]


class Migrator:
    def __init__(self, *migrations: SchemaMigrationProtocol):
        self.migrations = sorted(migrations, key=lambda m: m.from_version())
        self._messages = []
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
            if migration.from_version() != out["schema_version"]:
                continue
            out = migration.migrate(out)
            out["schema_version"] += 1
            self._messages.extend(migration.messages())

        return dict(out)

    def messages(self):
        return self._messages
