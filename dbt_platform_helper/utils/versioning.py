import os
import re
import subprocess
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version
from pathlib import Path

import click
import requests

from dbt_platform_helper.constants import DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION
from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_FILE
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.config import ConfigProvider
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.semantic_version import (
    IncompatibleMajorVersionException,
)
from dbt_platform_helper.providers.semantic_version import (
    IncompatibleMinorVersionException,
)
from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.providers.semantic_version import VersionStatus
from dbt_platform_helper.providers.validation import ValidationException


class PlatformHelperVersions:
    def __init__(
        self,
        local_version: SemanticVersion = None,
        latest_release: SemanticVersion = None,
        platform_helper_file_version: SemanticVersion = None,
        platform_config_default: SemanticVersion = None,
        pipeline_overrides: dict[str, str] = None,
    ):
        self.local_version = local_version
        self.latest_release = latest_release
        self.platform_helper_file_version = platform_helper_file_version
        self.platform_config_default = platform_config_default
        self.pipeline_overrides = pipeline_overrides if pipeline_overrides else {}


class PlatformHelperVersionNotFoundException(PlatformException):
    def __init__(self):
        super().__init__(f"""Platform helper version could not be resolved.""")


class RequiredVersion:
    def __init__(self, io=None):
        self.io = io or ClickIOProvider()

    def get_required_platform_helper_version(
        self, pipeline: str = None, versions: PlatformHelperVersions = None
    ) -> str:
        if not versions:
            versions = get_platform_helper_versions()
        pipeline_version = versions.pipeline_overrides.get(pipeline)
        version_precedence = [
            pipeline_version,
            versions.platform_config_default,
            versions.platform_helper_file_version,
        ]
        non_null_version_precedence = [
            f"{v}" if isinstance(v, SemanticVersion) else v for v in version_precedence if v
        ]

        out = non_null_version_precedence[0] if non_null_version_precedence else None

        if not out:
            raise PlatformHelperVersionNotFoundException

        return out

    def get_required_version(self, pipeline=None):
        version = self.get_required_platform_helper_version(pipeline)
        self.io.info(version)
        return version

    def check_platform_helper_version_mismatch(self):
        if not running_as_installed_package():
            return

        versions = get_platform_helper_versions()
        local_version = versions.local_version
        platform_helper_file_version = SemanticVersion.from_string(
            self.get_required_platform_helper_version(versions=versions)
        )

        if not check_version_on_file_compatibility(local_version, platform_helper_file_version):
            message = (
                f"WARNING: You are running platform-helper v{local_version} against "
                f"v{platform_helper_file_version} specified by {PLATFORM_HELPER_VERSION_FILE}."
            )
            self.io.warn(message)


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
        SemanticVersion.from_string(copilot_version), get_github_released_version("aws/copilot-cli")
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

    return VersionStatus(aws_version, get_github_released_version("aws/aws-cli", True))


# TODO To be moved somewhere that will be really obvious it's making a network call so we
# don't make unneccessary calls in tests etc.
def get_github_released_version(repository: str, tags: bool = False) -> SemanticVersion:
    if tags:
        tags_list = requests.get(f"https://api.github.com/repos/{repository}/tags").json()
        versions = [SemanticVersion.from_string(v["name"]) for v in tags_list]
        versions.sort(reverse=True)
        return versions[0]

    package_info = requests.get(f"https://api.github.com/repos/{repository}/releases/latest").json()
    return SemanticVersion.from_string(package_info["tag_name"])


# TODO To be moved somewhere that will be really obvious it's making a network call so we
# don't make unneccessary calls in tests etc.
def _get_latest_release() -> SemanticVersion:
    package_info = requests.get("https://pypi.org/pypi/dbt-platform-helper/json").json()
    released_versions = package_info["releases"].keys()
    parsed_released_versions = [SemanticVersion.from_string(v) for v in released_versions]
    parsed_released_versions.sort(reverse=True)
    return parsed_released_versions[0]


# Resolves all the versions from pypi, config and locally installed version
# echos warnings if anything is incompatible
def get_platform_helper_versions(include_project_versions=True) -> PlatformHelperVersions:
    try:
        locally_installed_version = SemanticVersion.from_string(version("dbt-platform-helper"))
    except PackageNotFoundError:
        locally_installed_version = None

    latest_release = _get_latest_release()

    if not include_project_versions:
        return PlatformHelperVersions(
            local_version=locally_installed_version,
            latest_release=latest_release,
        )

    deprecated_version_file = Path(PLATFORM_HELPER_VERSION_FILE)
    version_from_file = (
        SemanticVersion.from_string(deprecated_version_file.read_text())
        if deprecated_version_file.exists()
        else None
    )

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

    out = PlatformHelperVersions(
        local_version=locally_installed_version,
        latest_release=latest_release,
        platform_helper_file_version=version_from_file,
        platform_config_default=platform_config_default,
        pipeline_overrides=pipeline_overrides,
    )

    _process_version_file_warnings(out)

    return out


# Validates the returned PlatformHelperVersions and echos useful warnings
# Should use IO provider
# Could return ValidationMessages (warnings and errors) which are output elsewhere
def _process_version_file_warnings(versions: PlatformHelperVersions):
    if versions.platform_config_default and not versions.platform_helper_file_version:
        return

    messages = []
    missing_default_version_message = f"Create a section in the root of '{PLATFORM_CONFIG_FILE}':\n\ndefault_versions:\n  platform-helper: "
    deprecation_message = f"Please delete '{PLATFORM_HELPER_VERSION_FILE}' as it is now deprecated."

    if versions.platform_config_default and versions.platform_helper_file_version:
        messages.append(deprecation_message)

    if not versions.platform_config_default and versions.platform_helper_file_version:
        messages.append(deprecation_message)
        messages.append(
            f"{missing_default_version_message}{versions.platform_helper_file_version}\n"
        )

    if not versions.platform_config_default and not versions.platform_helper_file_version:
        message = f"Cannot get dbt-platform-helper version from '{PLATFORM_CONFIG_FILE}'.\n"
        message += f"{missing_default_version_message}{versions.local_version}\n"
        click.secho(message, fg="red")

    if messages:
        click.secho("\n".join(messages), fg="yellow")


# Generic function can stay utility for now
def check_version_on_file_compatibility(
    app_version: SemanticVersion, file_version: SemanticVersion
):
    app_major, app_minor, app_patch = app_version.major, app_version.minor, app_version.patch
    file_major, file_minor, file_patch = file_version.major, file_version.minor, file_version.patch

    return app_major == file_major and app_minor == file_minor and app_patch == file_patch


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


# TODO Only used in config command.  Move to config domain.  Move tests also.
def validate_template_version(app_version: SemanticVersion, template_file_path: str):
    app_version.validate_compatibility_with(get_template_generated_with_version(template_file_path))


# TODO called at the beginning of every command.  This is platform-version base functionality
def check_platform_helper_version_needs_update():
    if not running_as_installed_package() or "PLATFORM_TOOLS_SKIP_VERSION_CHECK" in os.environ:
        return

    versions = get_platform_helper_versions(include_project_versions=False)
    local_version = versions.local_version
    latest_release = versions.latest_release
    message = (
        f"You are running platform-helper v{local_version}, upgrade to "
        f"v{latest_release} by running run `pip install "
        "--upgrade dbt-platform-helper`."
    )
    try:
        local_version.validate_compatibility_with(latest_release)
    except IncompatibleMajorVersionException:
        click.secho(message, fg="red")
    except IncompatibleMinorVersionException:
        click.secho(message, fg="yellow")


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
