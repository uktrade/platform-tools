from dbt_platform_helper.providers.schema_migrations.schema_v0_to_v1_migration import (
    SchemaV0ToV1Migration,
)


def assert_original_config_is_not_modified(migrated_config, original_config):
    assert migrated_config != original_config


class TestSchemaV0ToV1Migration:
    def test_from_version(self):
        migration = SchemaV0ToV1Migration()

        assert migration.from_version() == 0

    def test_removes_terraform_platform_modules_version_from_defaults(self):
        migration = SchemaV0ToV1Migration()
        original_config = {
            "default_versions": {"terraform-platform-modules": "5.1.0", "platform-helper": "14.0.0"}
        }

        migrated_config = migration.migrate(original_config)

        assert_original_config_is_not_modified(migrated_config, original_config)
        assert migrated_config == {"default_versions": {"platform-helper": "14.0.0"}}

    def test_removes_version_overrides_from_envs(self):
        migration = SchemaV0ToV1Migration()
        original_config = {
            "environments": {
                "*": {
                    "requires_approval": False,
                },
                "dev": {"versions": {"terraform-platform-modules": "5.0.0"}},
                "staging": None,
            }
        }

        migrated_config = migration.migrate(original_config)

        expected_config = {
            "environments": {
                "*": {
                    "requires_approval": False,
                },
                "dev": {},
                "staging": None,
            }
        }
        assert_original_config_is_not_modified(migrated_config, original_config)
        assert migrated_config == expected_config

    def test_removes_from_and_to_account_from_postgres_extensions(self):
        migration = SchemaV0ToV1Migration()
        original_config = {
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

        migrated_config = migration.migrate(original_config)

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

        assert_original_config_is_not_modified(migrated_config, original_config)
        assert migrated_config == exp_config
