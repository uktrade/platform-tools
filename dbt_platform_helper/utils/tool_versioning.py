import re
import subprocess

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.semantic_version import VersionStatus
from dbt_platform_helper.providers.version import GithubVersionProvider


def get_required_terraform_platform_modules_version(
    cli_terraform_platform_modules_version, platform_config_terraform_modules_default_version
):
    version_preference_order = [
        cli_terraform_platform_modules_version,
        platform_config_terraform_modules_default_version,
        DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION,
    ]
    return [version for version in version_preference_order if version][0]


##################################################################################
# Only used in Config domain
# TODO Relocate along with tests when we refactor config command in DBTP-1538
##################################################################################


# Local version and latest release of tool.
# Used only in config command.
# TODO Move to config domain
def get_copilot_versions() -> VersionStatus:
    copilot_version = None

    try:
        response = subprocess.run("copilot --version", capture_output=True, shell=True)
        [copilot_version] = re.findall(r"[0-9.]+", response.stdout.decode("utf8"))
    except ValueError:
        pass

    return VersionStatus(
        SemanticVersion.from_string(copilot_version),
        GithubVersionProvider.get_latest_version("aws/copilot-cli"),
    )


# Local version and latest release of tool.
# Used only in config command.
# TODO Move to config domain
def get_aws_versions() -> VersionStatus:
    aws_version = None
    try:
        response = subprocess.run("aws --version", capture_output=True, shell=True)
        matched = re.match(r"aws-cli/([0-9.]+)", response.stdout.decode("utf8"))
        aws_version = SemanticVersion.from_string(matched.group(1))
    except ValueError:
        pass

    return VersionStatus(aws_version, GithubVersionProvider.get_latest_version("aws/aws-cli", True))
