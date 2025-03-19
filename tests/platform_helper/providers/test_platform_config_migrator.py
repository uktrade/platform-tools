from copy import deepcopy

from dbt_platform_helper.providers.platform_config_migration import (
    DeleteTerraformPlatformModulesVersions,
)
from dbt_platform_helper.providers.platform_config_migration import (
    PlatformConfigMigrator,
)


class SpyMigration:
    def __init__(self, name: str, is_applicable: bool):
        self.name = name
        self._is_applicable = is_applicable
        self.was_run = False

    def is_applicable(self, platform_config: dict) -> bool:
        return self._is_applicable

    def apply(self, platform_config: dict):
        self.was_run = True
        platform_config["migrations_that_ran"].append(self.name)

        return platform_config


def test_platform_config_migrator():
    platform_config = {"migrations_that_ran": []}
    platform_config_old = deepcopy(platform_config)

    spy1 = SpyMigration("spy1", True)
    spy2 = SpyMigration("spy2", False)
    spy3 = SpyMigration("spy3", True)

    pcm = PlatformConfigMigrator([spy1, spy2, spy3])
    new_config = pcm.migrate(platform_config)

    assert spy1.was_run
    assert not spy2.was_run

    assert new_config == {"migrations_that_ran": ["spy1", "spy3"]}
    assert platform_config == platform_config_old


def test_delete_terraform_platform_modules_version():
    platform_config = {
        "default_versions": {"terraform-platform-modules": "7.0.0", "platform-helper": "13.0.2"}
    }

    deleter = DeleteTerraformPlatformModulesVersions()

    assert deleter.is_applicable(platform_config)
    assert deleter.apply(platform_config) == {"default_versions": {"platform-helper": "13.0.2"}}


def test_delete_terraform_platform_modules_versions_from_environments():
    platform_config = {
        "environments": {
            "*": {"accounts": {"deploy": {"name": "non-prod-account"}}},
            "dev": {"versions": {"terraform-platform-modules": "5.0.0"}},
            "prod": {
                "accounts": {"deploy": {"name": "prod-account"}},
                "versions": {"terraform-platform-modules": "6.0.0"},
            },
        }
    }

    deleter = DeleteTerraformPlatformModulesVersions()

    expected = {
        "environments": {
            "*": {"accounts": {"deploy": {"name": "non-prod-account"}}},
            "dev": {"versions": {}},
            "prod": {"accounts": {"deploy": {"name": "prod-account"}}, "versions": {}},
        }
    }
    assert deleter.is_applicable(platform_config)
    assert deleter.apply(platform_config) == expected
