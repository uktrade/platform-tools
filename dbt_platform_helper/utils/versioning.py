import re
import subprocess
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version
from pathlib import Path

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_FILE
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.semantic_version import PlatformHelperVersionStatus
from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.semantic_version import VersionStatus
from dbt_platform_helper.providers.validation import ValidationException
from dbt_platform_helper.providers.version import GithubVersionProvider
from dbt_platform_helper.providers.version import PyPiVersionProvider
from dbt_platform_helper.providers.yaml_file import FileProviderException
from dbt_platform_helper.providers.yaml_file import YamlFileProvider


class PlatformHelperVersionNotFoundException(PlatformException):
    def __init__(self):
        super().__init__(f"""Platform helper version could not be resolved.""")


class RequiredVersion:
    def __init__(self, io=None):
        self.io = io or ClickIOProvider()

    def get_required_platform_helper_version(
        self, pipeline: str = None, version_status: PlatformHelperVersionStatus = None
    ) -> str:
        pipeline_version = version_status.pipeline_overrides.get(pipeline)
        version_precedence = [
            pipeline_version,
            version_status.platform_config_default,
            version_status.deprecated_version_file,
        ]
        non_null_version_precedence = [
            f"{v}" if isinstance(v, SemanticVersion) else v for v in version_precedence if v
        ]

        out = non_null_version_precedence[0] if non_null_version_precedence else None

        if not out:
            raise PlatformHelperVersionNotFoundException

        return out

    def get_required_version(self, pipeline=None):
        version_status = get_platform_helper_version_status()
        self.io.process_messages(version_status.warn())
        required_version = self.get_required_platform_helper_version(pipeline, version_status)
        self.io.info(required_version)
        return required_version

    # Used in the generate command
    def check_platform_helper_version_mismatch(self):
        if not running_as_installed_package():
            return

        version_status = get_platform_helper_version_status()

        self.io.process_messages(version_status.warn())

        required_version = SemanticVersion.from_string(
            self.get_required_platform_helper_version(version_status=version_status)
        )

        if not version_status.local == required_version:
            message = (
                f"WARNING: You are running platform-helper v{version_status.local} against "
                f"v{required_version} specified for the project."
            )
            self.io.warn(message)


# Resolves all the versions from pypi, config and locally installed version
def get_platform_helper_version_status(
    include_project_versions=True, yaml_provider=YamlFileProvider
) -> PlatformHelperVersionStatus:
    try:
        locally_installed_version = SemanticVersion.from_string(version("dbt-platform-helper"))
    except PackageNotFoundError:
        locally_installed_version = None

    latest_release = PyPiVersionProvider.get_latest_version("dbt-platform-helper")

    if not include_project_versions:
        return PlatformHelperVersionStatus(
            local=locally_installed_version,
            latest=latest_release,
        )

    deprecated_version_file = Path(PLATFORM_HELPER_VERSION_FILE)
    try:
        loaded_version = yaml_provider.load(deprecated_version_file)
        version_from_file = SemanticVersion.from_string(loaded_version)
    except FileProviderException:
        version_from_file = None

    platform_config_default, pipeline_overrides = None, {}

    config = ConfigProvider()
    platform_config = config.load_unvalidated_config_file()

    if platform_config:
        platform_config_default = SemanticVersion.from_string(
            platform_config.get("default_versions", {}).get("platform-helper")
        )

        pipeline_overrides = {
            name: pipeline.get("versions", {}).get("platform-helper")
            for name, pipeline in platform_config.get("environment_pipelines", {}).items()
            if pipeline.get("versions", {}).get("platform-helper")
        }

    out = PlatformHelperVersionStatus(
        local=locally_installed_version,
        latest=latest_release,
        deprecated_version_file=version_from_file,
        platform_config_default=platform_config_default,
        pipeline_overrides=pipeline_overrides,
    )

    return out


# TODO can stay as utility for now
def running_as_installed_package():
    return "site-packages" in __file__


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


# Getting version from the "Generated by" comment in a file that was generated from a template
# TODO where does this belong?  It sort of belongs to our platform-helper templating
def get_template_generated_with_version(template_file_path: str) -> SemanticVersion:
    try:
        template_contents = Path(template_file_path).read_text()
        template_version = re.match(
            r"# Generated by platform-helper ([v.\-0-9]+)", template_contents
        ).group(1)
        return SemanticVersion.from_string(template_version)
    except (IndexError, AttributeError):
        raise ValidationException(f"Template {template_file_path} has no version information")


def validate_template_version(app_version: SemanticVersion, template_file_path: str):
    app_version.validate_compatibility_with(get_template_generated_with_version(template_file_path))


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
