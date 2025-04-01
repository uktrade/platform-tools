import pytest

from dbt_platform_helper.providers.schema_migrations import (
    InvalidMigrationConfigurationException,
)
from dbt_platform_helper.providers.schema_migrations import Migrator
from dbt_platform_helper.providers.schema_migrations import SchemaV1ToV2Migration


class TestSchemaV1ToV2Migration:
    def test_from_version(self):
        migration = SchemaV1ToV2Migration()

        assert migration.from_version() == 1

    def test_removes_terraform_platform_modules_version_from_defaults(self):
        migration = SchemaV1ToV2Migration()
        config = {
            "default_versions": {"terraform-platform-modules": "5.1.0", "platform-helper": "14.0.0"}
        }

        actual_config = migration.migrate(config)

        # Ensure the migrate does not modify the original
        assert actual_config != config
        assert actual_config == {"default_versions": {"platform-helper": "14.0.0"}}

    def test_removes_version_overrides_from_envs(self):
        migration = SchemaV1ToV2Migration()
        config = {
            "environments": {
                "*": {
                    "requires_approval": False,
                },
                "dev": {"versions": {"terraform-platform-modules": "5.0.0"}},
                "staging": None,
            }
        }

        actual_config = migration.migrate(config)

        expected_config = {
            "environments": {
                "*": {
                    "requires_approval": False,
                },
                "dev": {},
                "staging": None,
            }
        }
        # Ensure migrate does not modify the original
        assert actual_config != config
        assert actual_config == expected_config

    def test_removes_from_and_to_account_from_postgres_extensions(self):
        migration = SchemaV1ToV2Migration()
        config = {
            "extensions": {
                "first_postgres": {
                    "type": "postgres",
                    "database_copy": [
                        {
                            "from": "prod",
                            "to": "hotfix",
                            "from_account": "1234556",
                            "to_account": "8888777",
                            "pipeline": {"schedule": "0 0 2 * * *"},
                        }
                    ],
                },
                "second_postgres": {
                    "type": "postgres",
                    "database_copy": [
                        {
                            "from": "prod",
                            "to": "hotfix",
                            "from_account": "45563323",
                            "to_account": "9998777",
                        }
                    ],
                },
            }
        }

        actual_config = migration.migrate(config)

        exp_config = {
            "extensions": {
                "first_postgres": {
                    "type": "postgres",
                    "database_copy": [
                        {"from": "prod", "to": "hotfix", "pipeline": {"schedule": "0 0 2 * * *"}}
                    ],
                },
                "second_postgres": {
                    "type": "postgres",
                    "database_copy": [
                        {
                            "from": "prod",
                            "to": "hotfix",
                        }
                    ],
                },
            }
        }

        # Ensure migrate does not modify the original
        assert actual_config != config
        assert actual_config == exp_config


class MockMigration:
    def __init__(self, name, from_version, call_record_list):
        self.name = name
        self._from_version = from_version
        self.call_record_list = call_record_list

    def from_version(self) -> int:
        return self._from_version

    def to_version(self) -> int:
        return self._to_version

    def migrate(self, platform_config: dict) -> dict:
        self.call_record_list.append(self.name)
        return platform_config


class TestMigrator:
    def test_migration_ordering(self):
        call_record = []
        migration1 = MockMigration("one", 4, call_record)
        migration2 = MockMigration("two", 1, call_record)
        migration3 = MockMigration("three", 3, call_record)
        migration4 = MockMigration("four", 2, call_record)

        migrator = Migrator(migration1, migration2, migration3, migration4)

        migrator.migrate({})

        assert call_record == ["two", "four", "three", "one"]

    def test_migration_migrations_cannot_have_same_from_version(self):
        call_record = []
        migration1 = MockMigration("one", 3, call_record)
        migration2 = MockMigration("two", 1, call_record)
        migration3 = MockMigration("three", 3, call_record)
        migration4 = MockMigration("four", 1, call_record)

        with pytest.raises(InvalidMigrationConfigurationException) as ex:
            Migrator(migration1, migration2, migration3, migration4)

        assert f"{ex.value}" == "`from_version` parameters must be unique amongst migrations"

    def test_migrations_adds_version_for_unversioned_config(self):
        migrator = Migrator()

        actual_config = migrator.migrate({})

        assert actual_config == {"schema_version": 1}

    def test_migrations_bump_schema_version_correctly(self):
        call_record = []
        migration1 = MockMigration("one", 1, call_record)
        migration2 = MockMigration("two", 2, call_record)
        migrator = Migrator(migration1, migration2)

        actual_config = migrator.migrate({"schema_version": 1})

        assert actual_config == {"schema_version": 3}

    def test_migrations_only_runs_for_migrations_targeting_schema_version_or_later(self):
        call_record = []
        migration1 = MockMigration("one", 1, call_record)
        migration2 = MockMigration("two", 2, call_record)
        migration3 = MockMigration("three", 3, call_record)
        migration4 = MockMigration("four", 4, call_record)
        migrator = Migrator(migration1, migration2, migration3, migration4)

        actual_config = migrator.migrate({"schema_version": 3})

        assert actual_config == {"schema_version": 5}
        assert call_record == ["three", "four"]
