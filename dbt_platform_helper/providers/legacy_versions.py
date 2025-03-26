class LegacyVersionsProvider:

    def check_terraform_platform_modules_version(
        self, io, cli_terraform_platform_modules_version, config
    ):
        has_deprecated_default = config.get("default_versions", {}).get(
            "terraform-platform-modules"
        )

        has_deprecated_version = any(
            "versions" in env and "terraform-platform-modules" in env["versions"]
            for env in config.get("environments", {}).values()
            if isinstance(env, dict)
        )

        if (
            cli_terraform_platform_modules_version
            or has_deprecated_default
            or has_deprecated_version
        ):
            io.warn(
                "The `--terraform-platform-modules-version` flag for the pipeline generate command is deprecated. "
                "Please use the `--platform-helper-version` flag instead.\n\n"
                "The `terraform-platform-modules` key set in the platform-config.yml file in the following locations: `default_versions: terraform-platform-modules` and "
                "`environments: <env>: versions: terraform-platform-modules`, are now deprecated. "
                "Please use the `default_versions: platform-helper` value instead. "
                "See full platform config reference in the docs: "
                "https://platform.readme.trade.gov.uk/reference/platform-config-yml/#core-configuration"
            )
            return None
