import pytest
import yaml

from dbt_platform_helper.providers.schema_migrator import (
    InvalidMigrationConfigurationException,
)
from dbt_platform_helper.providers.schema_migrator import Migrator


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
    def test_migrator_migration_ordering(self):
        call_record = []
        migration1 = MockMigration("one", 3, call_record)
        migration2 = MockMigration("two", 0, call_record)
        migration3 = MockMigration("three", 2, call_record)
        migration4 = MockMigration("four", 1, call_record)

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

        assert actual_config == {"schema_version": 0}

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

    @pytest.mark.parametrize(
        "keys",
        [
            [
                "pre",
                "application",
                "padding1",
                "schema_version",
                "padding2",
                "default_versions",
                "post",
            ],
            [
                "pre",
                "default_versions",
                "padding1",
                "schema_version",
                "padding2",
                "application",
                "post",
            ],
            ["pre", "schema_version", "mid", "default_versions", "post"],
            ["pre", "default_versions", "mid", "application", "post"],
            ["pre", "schema_version", "mid", "application", "post"],
            ["pre", "application", "post"],
            ["pre", "schema_version", "post"],
            ["pre", "default_versions", "post"],
        ],
    )
    def test_migrate_ensures_application_schema_version_and_default_versions_are_at_the_top_if_they_exist(
        self, keys
    ):
        migrator = Migrator()

        config = {}

        for key in keys:
            config[key] = key

        actual_config = migrator.migrate(config)

        expected_key_set = set(keys)
        expected_key_set.add("schema_version")

        expected_order = [
            key
            for key in ["application", "schema_version", "default_versions"]
            if key in expected_key_set
        ]

        as_yaml = yaml.dump(
            actual_config,
            canonical=False,
            sort_keys=False,
            default_style=None,
            default_flow_style=False,
        ).splitlines()

        for i, exp_key in enumerate(expected_order):
            assert exp_key in as_yaml[i]
