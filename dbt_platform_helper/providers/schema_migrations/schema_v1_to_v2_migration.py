from copy import deepcopy


class SchemaV1ToV2Migration:
    def from_version(self) -> int:
        return 1

    def migrate(self, platform_config: dict) -> dict:
        migrated_config = deepcopy(platform_config)

        self._remove_prod_account_pipelines(migrated_config)
        self._remove_trigger_and_account_from_environment_pipelines(migrated_config)

        return migrated_config

    def _remove_prod_account_pipelines(self, migrated_config: dict) -> None:
        prod_account = (
            migrated_config.get("environments", {})
            .get("prod", {})
            .get("accounts", {})
            .get("deploy", {})
            .get("name")
        )
        if not prod_account:
            return

        pipelines_to_remove = []
        for pipeline_name, pipeline in migrated_config.get("environment_pipelines", {}).items():
            if "pipeline_to_trigger" in pipeline:
                triggered_pipeline_name = pipeline["pipeline_to_trigger"]
                triggered_pipeline_config = migrated_config["environment_pipelines"][
                    triggered_pipeline_name
                ]

                if triggered_pipeline_config["account"] == prod_account:
                    pipelines_to_remove.append(triggered_pipeline_name)
                    pipeline["environments"].update(triggered_pipeline_config["environments"])

        for pipeline_name in pipelines_to_remove:
            del migrated_config["environment_pipelines"][pipeline_name]

    def _remove_trigger_and_account_from_environment_pipelines(self, migrated_config: dict) -> None:
        for pipeline_name, pipeline in migrated_config.get("environment_pipelines", {}).items():
            if "account" in pipeline:
                del pipeline["account"]
            if "pipeline_to_trigger" in pipeline:
                del pipeline["pipeline_to_trigger"]
