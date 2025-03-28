from typing import Any
from typing import Dict
from typing import Optional

from dbt_platform_helper.providers.io import ClickIOProvider


class LegacyVersionsProvider:

    def __init__(self, io: ClickIOProvider = ClickIOProvider()):
        self.io: ClickIOProvider = io

    def check_terraform_platform_modules_version(
        self, cli_terraform_platform_modules_version: Optional[str], config: Dict[str, Any]
    ):
        has_deprecated_default = config.get("default_versions", {}).get(
            "terraform-platform-modules"
        )

        has_deprecated_version = any(
            isinstance(env, dict)
            and "versions" in env
            and isinstance(env["versions"], dict)
            and "terraform-platform-modules" in env["versions"]
            for key, env in config.get("environments", {}).items()
            if key != "default_versions"
        )

        if cli_terraform_platform_modules_version:
            self.io.warn(
                "The `--terraform-platform-modules-version` flag for the pipeline generate command is deprecated. "
                "Please use the `--platform-helper-version` flag instead.\n"
            )

        if has_deprecated_default:
            self.io.warn(
                "The `terraform-platform-modules` key set in the platform-config.yml file in the following location: `default_versions: terraform-platform-modules` is now deprecated. "
                "Please use the `default_versions: platform-helper` value instead. "
                "See full platform config reference in the docs: "
                "https://platform.readme.trade.gov.uk/reference/platform-config-yml/#core-configuration.\n"
            )

        if has_deprecated_version:
            self.io.warn(
                "The `terraform-platform-modules` key set in the platform-config.yml file in the following location:  `environments: <env>: versions: terraform-platform-modules` is now deprecated. "
                "Please use the `default_versions: platform-helper` value instead. "
                "See full platform config reference in the docs: "
                "https://platform.readme.trade.gov.uk/reference/platform-config-yml/#core-configuration.\n"
            )
