from copy import deepcopy
from typing import Protocol

TPM_VERSION_KEY = "terraform-platform-modules"


class Migration(Protocol):
    def is_applicable(self, platform_config: dict) -> bool: ...

    def apply(self, platform_config: dict) -> dict: ...


class PlatformConfigMigrator:
    def __init__(self, migrations: list[Migration]):
        self.migrations = migrations

    def migrate(self, platform_config: dict):
        current_config = deepcopy(platform_config)

        for migration in self.migrations:
            if migration.is_applicable(current_config):
                current_config = migration.apply(current_config)

        return current_config


class DeleteTerraformPlatformModulesVersions:
    def is_applicable(self, platform_config: dict) -> bool:
        default_versions = platform_config.get("default_versions", {})
        if TPM_VERSION_KEY in default_versions:
            return True

        environments = platform_config.get("environments", {})
        for env_name, env in environments.items():
            versions = env.get("versions", {})
            if TPM_VERSION_KEY in versions:
                return True
        return False

    def apply(self, platform_config: dict) -> dict:
        default_versions = platform_config.get("default_versions", {})
        if TPM_VERSION_KEY in default_versions:
            del default_versions[TPM_VERSION_KEY]

        environments = platform_config.get("environments", {})
        for env_name, env in environments.items():
            versions = env.get("versions", {})
            if TPM_VERSION_KEY in versions:
                del versions[TPM_VERSION_KEY]
        return platform_config
