from copy import deepcopy


class SchemaV0ToV1Migration:
    def from_version(self) -> int:
        return 0

    def migrate(self, platform_config: dict) -> dict:
        migrated_config = deepcopy(platform_config)

        self._remove_terraform_platform_modules_default_version(migrated_config)
        self._remove_versions_from_env_config(migrated_config)
        self._remove_to_account_and_from_account_from_database_copy(migrated_config)
        self._remove_pipeline_platform_helper_override(migrated_config)

        return migrated_config

    def _remove_versions_from_env_config(self, migrated_config: dict) -> None:
        for env_name, env in migrated_config.get("environments", {}).items():
            if env and "versions" in env:
                del env["versions"]

    def _remove_terraform_platform_modules_default_version(self, migrated_config: dict) -> None:
        if "default_versions" in migrated_config:
            default_versions = migrated_config["default_versions"]
            if "terraform-platform-modules" in default_versions:
                del default_versions["terraform-platform-modules"]

    def _remove_to_account_and_from_account_from_database_copy(self, migrated_config: dict) -> None:
        for extension_name, extension in migrated_config.get("extensions", {}).items():
            if extension.get("type") == "postgres" and "database_copy" in extension:
                for database_copy_block in extension["database_copy"]:
                    if "from_account" in database_copy_block:
                        del database_copy_block["from_account"]
                    if "to_account" in database_copy_block:
                        del database_copy_block["to_account"]

    def _remove_pipeline_platform_helper_override(self, migrated_config: dict) -> None:
        for pipeline_name, pipeline_config in migrated_config.get(
            "environment_pipelines", {}
        ).items():
            if "versions" in pipeline_config:
                del pipeline_config["versions"]
