import os
import re
import webbrowser
from pathlib import Path
from typing import Dict

from prettytable import PrettyTable

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.domain.versioning import AWSVersioning
from dbt_platform_helper.domain.versioning import CopilotVersioning
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.entities.semantic_version import (
    IncompatibleMajorVersionException,
)
from dbt_platform_helper.entities.semantic_version import SemanticVersion
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.aws.sso_auth import SSOAuthProvider
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.schema_migrator import ALL_MIGRATIONS
from dbt_platform_helper.providers.schema_migrator import Migrator
from dbt_platform_helper.providers.validation import ValidationException
from dbt_platform_helper.providers.version_status import VersionStatus

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

AWS_CONFIG = """
#
# uktrade
#

[sso-session uktrade]
sso_start_url = https://uktrade.awsapps.com/start#/
sso_region = eu-west-2
sso_registration_scopes = sso:account:access

[default]
sso_session = uktrade
region = eu-west-2
output = json

"""


class NoDeploymentRepoConfigException(PlatformException):
    def __init__(self):
        super().__init__("Could not find a deployment repository, no checks to run.")


# TODO: DBTP-1993: move to generic location so it can be reused
class NoPlatformConfigException(PlatformException):
    def __init__(self):
        super().__init__(
            f"`platform-config.yml` is missing. "
            "Please check it exists and you are in the root directory of your deployment project."
        )


class Config:
    def __init__(
        self,
        io: ClickIOProvider = ClickIOProvider(),
        platform_helper_versioning: PlatformHelperVersioning = PlatformHelperVersioning(),
        aws_versioning: AWSVersioning = AWSVersioning(),
        copilot_versioning: CopilotVersioning = CopilotVersioning(),
        sso: SSOAuthProvider = None,
        config_provider: ConfigProvider = ConfigProvider(),
        migrator: Migrator = Migrator(ALL_MIGRATIONS, io_provider=ClickIOProvider()),
    ):
        self.oidc_app = None
        self.io = io
        self.platform_helper_versioning = platform_helper_versioning
        self.aws_versioning = aws_versioning
        self.copilot_versioning = copilot_versioning
        self.sso = sso or SSOAuthProvider()
        self.SSO_START_URL = "https://uktrade.awsapps.com/start"
        self.config_provider = config_provider
        self.migrator = migrator

    def validate(self):
        if not Path("copilot").exists():
            raise NoDeploymentRepoConfigException()
        if not Path(PLATFORM_CONFIG_FILE).exists():
            raise NoPlatformConfigException()

        self.io.debug("\nDetected a deployment repository\n")
        platform_helper_version_status = self.platform_helper_versioning.get_version_status()
        aws_version_status = self.aws_versioning.get_version_status()
        copilot_version_status = self.copilot_versioning.get_version_status()

        self._check_tool_versions(
            platform_helper_version_status, aws_version_status, copilot_version_status
        )

        compatible = self._check_addon_versions(platform_helper_version_status)

        exit(0 if compatible else 1)

    def migrate(self):
        platform_config = self.config_provider.load_unvalidated_config_file()
        new_platform_config = self.migrator.migrate(platform_config)
        self.config_provider.write_platform_config(new_platform_config)

    def generate_aws(self, file_path):
        self.oidc_app = self._create_oidc_application()
        verification_url, device_code = self._get_device_code(self.oidc_app)

        if self.io.confirm(
            "You are about to be redirected to a verification page. You will need to complete sign-in before returning to the command line. Do you want to continue?",
        ):
            webbrowser.open(verification_url)

        if self.io.confirm(
            "Have you completed the sign-in process in your browser?",
        ):
            access_token = self.sso.create_access_token(
                client_id=self.oidc_app[0],
                client_secret=self.oidc_app[1],
                device_code=device_code,
            )

        aws_config_path = os.path.expanduser(file_path)

        if self.io.confirm(
            f"This command is destructive and will overwrite file contents at {file_path}. Are you sure you want to continue?"
        ):
            with open(aws_config_path, "w") as config_file:
                config_file.write(AWS_CONFIG)

                for account in self._retrieve_aws_accounts(access_token):
                    config_file.write(f"[profile {account['accountName']}]\n")
                    config_file.write("sso_session = uktrade\n")
                    config_file.write(f"sso_account_id = {account['accountId']}\n")
                    config_file.write("sso_role_name = AdministratorAccess\n")
                    config_file.write("region = eu-west-2\n")
                    config_file.write("output = json\n")
                    config_file.write("\n")

    def _create_oidc_application(self):
        self.io.debug("Creating temporary AWS SSO OIDC application")
        client_id, client_secret = self.sso.register(
            client_name="platform-helper",
            client_type="public",
        )
        return client_id, client_secret

    def _get_device_code(self, oidc_application):
        self.io.debug("Initiating device code flow")
        url, device_code = self.sso.start_device_authorization(
            client_id=oidc_application[0],
            client_secret=oidc_application[1],
            start_url=self.SSO_START_URL,
        )

        return url, device_code

    def _retrieve_aws_accounts(self, aws_sso_token):
        accounts_list = self.sso.list_accounts(
            access_token=aws_sso_token,
            max_results=100,
        )
        return accounts_list

    def _add_version_status_row(
        self, table: PrettyTable, header: str, version_status: VersionStatus
    ):
        table.add_row(
            [
                header,
                str(version_status.installed),
                str(version_status.latest),
                no if version_status.is_outdated() else yes,
            ]
        )

    def _check_tool_versions(
        self,
        platform_helper_version_status: VersionStatus,
        aws_version_status: VersionStatus,
        copilot_version_status: VersionStatus,
    ):
        self.io.debug("Checking tooling versions...")

        recommendations = {}

        if copilot_version_status.installed is None:
            recommendations["install-copilot"] = RECOMMENDATIONS["install-copilot"]

        if aws_version_status.installed is None:
            recommendations["install-aws"] = RECOMMENDATIONS["install-aws"]

        tool_versions_table = PrettyTable()
        tool_versions_table.field_names = [
            "Tool",
            "Local version",
            "Released version",
            "Running latest?",
        ]
        tool_versions_table.align["Tool"] = "l"

        self._add_version_status_row(tool_versions_table, "aws", aws_version_status)
        self._add_version_status_row(tool_versions_table, "copilot", copilot_version_status)
        self._add_version_status_row(
            tool_versions_table, "dbt-platform-helper", platform_helper_version_status
        )

        self.io.info(tool_versions_table)

        if aws_version_status.is_outdated() and "install-aws" not in recommendations:
            recommendations["aws-upgrade"] = RECOMMENDATIONS["generic-tool-upgrade"].format(
                tool="AWS CLI",
                version=str(aws_version_status.latest),
            )

        if copilot_version_status.is_outdated() and "install-copilot" not in recommendations:
            recommendations["copilot-upgrade"] = RECOMMENDATIONS["generic-tool-upgrade"].format(
                tool="AWS Copilot",
                version=str(copilot_version_status.latest),
            )

        if platform_helper_version_status.is_outdated():
            recommendations["dbt-platform-helper-upgrade"] = RECOMMENDATIONS[
                "dbt-platform-helper-upgrade"
            ].format(version=str(platform_helper_version_status.latest))
            recommendations["dbt-platform-helper-upgrade-note"] = RECOMMENDATIONS[
                "dbt-platform-helper-upgrade-note"
            ]

        self._render_recommendations(recommendations)

    def _check_addon_versions(self, platform_helper_versions: VersionStatus) -> bool:

        self.io.debug("Checking addons templates versions...")

        compatible = True
        recommendations = {}

        local_version = platform_helper_versions.installed
        latest_release = platform_helper_versions.latest

        addons_templates_table = PrettyTable()
        addons_templates_table.field_names = [
            "Addons Template File",
            "Generated with",
            "Compatible with local?",
            "Compatible with latest?",
        ]
        addons_templates_table.align["Addons Template File"] = "l"

        addons_templates = list(Path("./copilot").glob("**/addons/*"))
        # Sort by template file path
        addons_templates.sort(key=lambda e: str(e))
        # Bring environment addons to the top
        addons_templates.sort(key=lambda e: "environments/" not in str(e))

        for template_file in addons_templates:
            generated_with_version = maybe
            local_compatible_symbol = yes
            latest_compatible_symbol = yes

            generated_with_version = None

            try:
                generated_with_version = self.__get_template_generated_with_version(
                    str(template_file.resolve())
                )
            except ValidationException:
                local_compatible_symbol = maybe
                compatible = False
                recommendations["dbt-platform-helper-upgrade"] = RECOMMENDATIONS[
                    "dbt-platform-helper-upgrade"
                ].format(version=latest_release)
                recommendations["dbt-platform-helper-upgrade-note"] = RECOMMENDATIONS[
                    "dbt-platform-helper-upgrade-note"
                ]

            try:
                local_version.validate_compatibility_with(generated_with_version)
            except IncompatibleMajorVersionException:
                local_compatible_symbol = no
                compatible = False
                recommendations["dbt-platform-helper-upgrade"] = RECOMMENDATIONS[
                    "dbt-platform-helper-upgrade"
                ].format(version=latest_release)
                recommendations["dbt-platform-helper-upgrade-note"] = RECOMMENDATIONS[
                    "dbt-platform-helper-upgrade-note"
                ]
            except ValidationException:
                local_compatible_symbol = maybe
                compatible = False

            try:
                latest_release.validate_compatibility_with(generated_with_version)
            except IncompatibleMajorVersionException:
                latest_compatible_symbol = no
                compatible = False
            except ValidationException:
                latest_compatible_symbol = maybe
                compatible = False

            addons_templates_table.add_row(
                [
                    template_file.relative_to("."),
                    (maybe if latest_compatible_symbol is maybe else str(generated_with_version)),
                    local_compatible_symbol,
                    latest_compatible_symbol,
                ]
            )

        self.io.info(addons_templates_table)
        self._render_recommendations(recommendations)

        return compatible

    def _render_recommendations(self, recommendations: Dict[str, str]):
        if recommendations:
            self.io.info("\nRecommendations:\n", bold=True)

            for name, recommendation in recommendations.items():
                if name.endswith("-note"):
                    continue
                self.io.info(f"  - {recommendation}")
                if recommendations.get(f"{name}-note", False):
                    self.io.info(f"    {recommendations.get(f'{name}-note')}")

            self.io.info("")

    def __get_template_generated_with_version(self, template_file_path: str) -> SemanticVersion:
        try:
            template_contents = Path(template_file_path).read_text()
            template_version = re.search(
                r"# Generated by platform-helper ([v.\-0-9]+)", template_contents
            ).group(1)
            return SemanticVersion.from_string(template_version)
        except (IndexError, AttributeError):
            raise ValidationException(f"Template {template_file_path} has no version information")
