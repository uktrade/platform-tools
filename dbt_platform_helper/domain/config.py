import os
import re
import webbrowser
from pathlib import Path
from typing import Dict

from prettytable import PrettyTable

from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.semantic_version import (
    IncompatibleMajorVersionException,
)
from dbt_platform_helper.providers.semantic_version import PlatformHelperVersionStatus
from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.semantic_version import VersionStatus
from dbt_platform_helper.providers.validation import ValidationException
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


class SSOAuthProvider:
    def __init__(self):
        pass

    def register(self, client_name, client_type):
        pass

    def start_device_authorization(self, client_id, client_secret, start_url):
        pass

    def create_access_token(self, client_id, client_secret, grant_type, device_code):
        pass

    def list_accounts(self, access_token, max_results):
        pass


class NoDeploymentRepoConfigException(PlatformException):
    def __init__(self):
        super().__init__("Could not find a deployment repository, no checks to run.")


class Config:

    def __init__(
        self,
        io: ClickIOProvider = ClickIOProvider(),
        platform_helper_versioning_domain: PlatformHelperVersioning = PlatformHelperVersioning(),
        get_aws_versions=get_aws_versions,
        get_copilot_versions=get_copilot_versions,
        sso: SSOAuthProvider = SSOAuthProvider(),
        config: ConfigProvider = ConfigProvider(),  # TODO in test inject mock IO here to assert
    ):
        self.io = io
        self.platform_helper_versioning_domain = platform_helper_versioning_domain
        self.get_aws_versions = get_aws_versions
        self.get_copilot_versions = get_copilot_versions
        self.config = config
        self.sso = sso
        self.SSO_START_URL = "https://uktrade.awsapps.com/start"

    def validate(self):
        if not Path("copilot").exists():
            raise NoDeploymentRepoConfigException()

        self.io.debug("\nDetected a deployment repository\n")
        platform_helper_version_status = self.platform_helper_versioning_domain._get_version_status(
            include_project_versions=True
        )
        self.io.process_messages(platform_helper_version_status.validate())
        aws_versions = self.get_aws_versions()
        copilot_versions = self.get_copilot_versions()

        self._check_tool_versions(platform_helper_version_status, aws_versions, copilot_versions)

        ConfigProvider().config_file_check()  # TODO move to top and make it a generic usable function? Where will it live?

        compatible = self._check_addon_versions(platform_helper_version_status)

        exit(0 if compatible else 1)

    def generate_aws(self, file_path):
        oidc_app = self._create_oidc_application()
        verification_url, device_code = self._get_device_code(oidc_app)

        # Should abort=True remain? We do not include any other args in the Provider interface
        if self.io.confirm(
            "You are about to be redirected to a verification page. You will need to complete sign-in before returning to the command line. Do you want to continue?",
        ):
            webbrowser.open(verification_url)

        if self.io.confirm(
            "Have you completed the sign-in process in your browser?",
        ):
            access_token = self._get_access_token(device_code, oidc_app)

        aws_config_path = os.path.expanduser(file_path)

        if self.io.confirm(
            f"This command is destructive and will overwrite file contents at {file_path}. Are you sure you want to continue?"
        ):
            with open(aws_config_path, "w") as config_file:
                config_file.write(AWS_CONFIG)

                for account in self._retrieve_aws_accounts(access_token):
                    config_file.write(f"[profile {account['account_name']}]\n")
                    config_file.write("sso_session = uktrade\n")
                    config_file.write(f"sso_account_id = {account['account_id']}\n")
                    config_file.write("sso_role_name = AdministratorAccess\n")
                    config_file.write("region = eu-west-2\n")
                    config_file.write("output = json\n")
                    config_file.write("\n")

    def _create_oidc_application(self):
        print("Creating temporary AWS SSO OIDC application")
        client = self.sso.register(
            client_name="platform-helper",
            client_type="public",
        )
        client_id = client.get("clientId")
        client_secret = client.get("clientSecret")

        return client_id, client_secret

    def _get_device_code(self, oidc_application):
        print("Initiating device code flow")
        authz = self.sso.start_device_authorization(
            client_id=oidc_application[0],
            client_secret=oidc_application[1],
            start_url=self.SSO_START_URL,
        )
        url = authz.get("verificationUriComplete")
        deviceCode = authz.get("deviceCode")

        return url, deviceCode

    def _get_access_token(self, device_code, oidc_app):
        try:
            access_token = self.sso.create_access_token(
                client_id=oidc_app[0],
                client_secret=oidc_app[1],
                grant_type="urn:ietf:params:oauth:grant-type:device_code",
                device_code=device_code,
            )

            return access_token

        # TODO: implement and raise from ClientError exception
        except Exception:
            pass

    def _retrieve_aws_accounts(self, aws_sso_token):
        accounts_list = self.sso.list_accounts(
            access_token=aws_sso_token,
            max_results=100,
        )
        if len(accounts_list) == 0:
            raise RuntimeError("Unable to retrieve AWS SSO account list\n")
        return accounts_list

    def _check_tool_versions(
        self,
        platform_helper_versions: PlatformHelperVersionStatus,
        aws_versions: VersionStatus,
        copilot_versions: VersionStatus,
    ):
        self.io.debug("Checking tooling versions...")

        recommendations = {}

        local_copilot_version = copilot_versions.installed
        copilot_latest_release = copilot_versions.latest
        if local_copilot_version is None:
            recommendations["install-copilot"] = RECOMMENDATIONS["install-copilot"]

        if aws_versions.installed is None:
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
                str(aws_versions.installed),
                str(aws_versions.latest),
                no if aws_versions.is_outdated() else yes,
            ]
        )
        tool_versions_table.add_row(
            [
                "copilot",
                str(copilot_versions.installed),
                str(copilot_versions.latest),
                no if copilot_versions.is_outdated() else yes,
            ]
        )
        tool_versions_table.add_row(
            [
                "dbt-platform-helper",
                str(platform_helper_versions.installed),
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

    def _check_addon_versions(self, platform_helper_versions: PlatformHelperVersionStatus) -> bool:

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
            # TODO just multi line this?
            self.io.info(
                "\nRecommendations:\n",
            )  # TODO re-add bold=True support

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
            template_version = re.match(
                r"# Generated by platform-helper ([v.\-0-9]+)", template_contents
            ).group(1)
            return SemanticVersion.from_string(template_version)
        except (IndexError, AttributeError):
            raise ValidationException(f"Template {template_file_path} has no version information")
