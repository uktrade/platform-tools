from pathlib import Path
from typing import Dict

from prettytable import PrettyTable

from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.yaml_file import YamlFileProvider
from dbt_platform_helper.utils.tool_versioning import get_aws_versions
from dbt_platform_helper.utils.tool_versioning import get_copilot_versions

yes = "\033[92m✔\033[0m"
no = "\033[91m✖\033[0m"
maybe = "\033[93m?\033[0m"

RECOMMENDATIONS = {
    "dbt-platform-helper-upgrade": (
        "Upgrade dbt-platform-helper to version {version} `pip install "
        "--upgrade dbt-platform-helper=={version}`."
    ),
    "dbt-platform-helper-upgrade-note": (
        "Post upgrade, run `platform-helper copilot make-addons` to " "update your addon templates."
    ),
    "generic-tool-upgrade": "Upgrade {tool} to version {version}.",
    "install-copilot": "Install AWS Copilot https://aws.github.io/copilot-cli/",
    "install-aws": "Install AWS CLI https://aws.amazon.com/cli/",
}


class NoDeploymentRepoConfigException(PlatformException):
    def __init__(self):
        super().__init__("Could not find a deployment repository, no checks to run.")


class Config:

    def __init__(
        self,
        io: ClickIOProvider = ClickIOProvider(),
        platform_helper_versioning_domain: PlatformHelperVersioning = PlatformHelperVersioning(
            version_file_version_provider=YamlFileProvider  # Overrides DeprecatedVersionFileVersionProvider wrapper
        ),
        get_aws_versions=get_aws_versions,
        get_copilot_versions=get_copilot_versions,
    ):
        self.io = io
        self.platform_helper_versioning_domain = platform_helper_versioning_domain
        self.get_aws_versions = get_aws_versions
        self.get_copilot_versions = get_copilot_versions

    def validate(self):
        if Path("copilot").exists():
            self.io.debug("\nDetected a deployment repository\n")
            platform_helper_version_status = (
                self.platform_helper_versioning_domain._get_version_status(
                    include_project_versions=True
                )
            )
            self.io.process_messages(platform_helper_version_status.validate())
            aws_versions = self.get_aws_versions()
            copilot_versions = self.get_copilot_versions()

            self._check_tool_versions(
                platform_helper_version_status, aws_versions, copilot_versions
            )
            self.io.debug("Checking addons templates versions...")
        else:
            raise NoDeploymentRepoConfigException()

    def generate_aws(self):
        pass

    def _check_tool_versions(self, platform_helper_versions, aws_versions, copilot_versions):
        self.io.debug("Checking tooling versions...")

        recommendations = {}

        local_copilot_version = copilot_versions.local
        copilot_latest_release = copilot_versions.latest
        if local_copilot_version is None:
            recommendations["install-copilot"] = RECOMMENDATIONS["install-copilot"]

        if aws_versions.local is None:
            recommendations["install-aws"] = RECOMMENDATIONS["install-aws"]

        tool_versions_table = PrettyTable()
        tool_versions_table.field_names = [
            "Tool",
            "Local version",
            "Released version",
            "Running latest?",
        ]
        tool_versions_table.align["Tool"] = "l"

        tool_versions_table.add_row(
            [
                "aws",
                str(aws_versions.local),
                str(aws_versions.latest),
                no if aws_versions.is_outdated() else yes,
            ]
        )
        tool_versions_table.add_row(
            [
                "copilot",
                str(copilot_versions.local),
                str(copilot_versions.latest),
                no if copilot_versions.is_outdated() else yes,
            ]
        )
        tool_versions_table.add_row(
            [
                "dbt-platform-helper",
                str(platform_helper_versions.local),
                str(platform_helper_versions.latest),
                no if platform_helper_versions.is_outdated() else yes,
            ]
        )

        self.io.info(tool_versions_table)

        if aws_versions.is_outdated() and "install-aws" not in recommendations:
            recommendations["aws-upgrade"] = RECOMMENDATIONS["generic-tool-upgrade"].format(
                tool="AWS CLI",
                version=str(aws_versions.latest),
            )

        if copilot_versions.is_outdated() and "install-copilot" not in recommendations:
            recommendations["copilot-upgrade"] = RECOMMENDATIONS["generic-tool-upgrade"].format(
                tool="AWS Copilot",
                version=str(copilot_latest_release),
            )

        if platform_helper_versions.is_outdated():
            recommendations["dbt-platform-helper-upgrade"] = RECOMMENDATIONS[
                "dbt-platform-helper-upgrade"
            ].format(version=str(platform_helper_versions.latest))
            recommendations["dbt-platform-helper-upgrade-note"] = RECOMMENDATIONS[
                "dbt-platform-helper-upgrade-note"
            ]

        self._render_recommendations(recommendations)

    def _render_recommendations(self, recommendations: Dict[str, str]):
        if recommendations:
            # TODO just multi line this?
            self.io.info(
                "\nRecommendations:\n",
            )  # bold=True

            for name, recommendation in recommendations.items():
                if name.endswith("-note"):
                    continue
                self.io.info(f"  - {recommendation}")
                if recommendations.get(f"{name}-note", False):
                    self.io.info(f"    {recommendations.get(f'{name}-note')}")

            self.io.info("")
