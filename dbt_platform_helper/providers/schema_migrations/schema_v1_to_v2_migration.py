import os
from copy import deepcopy
from pathlib import Path

from dbt_platform_helper.providers.files import FileProvider
from dbt_platform_helper.providers.io import ClickIOProvider

SERVICE_TYPES = ["Load Balanced Web Service", "Backend Service"]


class SchemaV1ToV2Migration:
    def from_version(self) -> int:
        return 1

    def migrate(self, platform_config: dict) -> dict:
        migrated_config = deepcopy(platform_config)

        self._create_services_directory_and_config_files()

        return migrated_config

    def _create_services_directory_and_config_files(self) -> None:
        service_directory = Path("services/")
        service_directory.mkdir(parents=True, exist_ok=True)

        for dirname, _, filenames in os.walk("copilot"):
            if "manifest.yml" in filenames and "environments" not in dirname:
                with open(f"{dirname}/manifest.yml") as f:
                    copilot_manifest = yaml.safe_load(f.read())

                    if copilot_manifest["type"] in SERVICE_TYPES:
                        service_name = copilot_manifest["name"]
                        service_path = service_directory / service_name

                        del copilot_manifest["type"]

                        ClickIOProvider().info(
                            FileProvider.mkfile(
                                service_path,
                                "service-config.yml",
                                yaml.safe_dump(copilot_manifest),
                                overwrite=True,
                            )
                        )
