import os
import re
import subprocess
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version
from pathlib import Path
from typing import Optional
from typing import Tuple
from typing import Union

import click
import requests

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_FILE
from dbt_platform_helper.exceptions import IncompatibleMajorVersion
from dbt_platform_helper.exceptions import IncompatibleMinorVersion
from dbt_platform_helper.exceptions import ValidationException
from dbt_platform_helper.utils.platform_config import load_unvalidated_config_file

VersionTuple = Optional[Tuple[int, int, int]]


class Versions:
    def __init__(self, local_version: VersionTuple = None, latest_release: VersionTuple = None):
        self.local_version = local_version
        self.latest_release = latest_release


class PlatformHelperVersions:
    def __init__(
        self,
        local_version: VersionTuple = None,
        latest_release: VersionTuple = None,
        platform_helper_file_version: VersionTuple = None,
        platform_config_default: VersionTuple = None,
        pipeline_overrides: dict[str, str] = None,
    ):
        self.local_version = local_version
        self.latest_release = latest_release
        self.platform_helper_file_version = platform_helper_file_version
        self.platform_config_default = platform_config_default
        self.pipeline_overrides = pipeline_overrides if pipeline_overrides else {}


def string_version(input_version: VersionTuple) -> str:
    if input_version is None:
        return "unknown"
    major, minor, patch = input_version
    return ".".join([str(s) for s in [major, minor, patch]])


def parse_version(input_version: Union[str, None]) -> VersionTuple:
    if input_version is None:
        return None

    version_plain = input_version.replace("v", "")
    version_segments = re.split(r"[.\-]", version_plain)

    if len(version_segments) != 3:
        return None

    output_version = [0, 0, 0]
    for index, segment in enumerate(version_segments):
        try:
            output_version[index] = int(segment)
        except ValueError:
            output_version[index] = -1
    return output_version[0], output_version[1], output_version[2]


def get_copilot_versions() -> Versions:
    copilot_version = None

    try:
        response = subprocess.run("copilot --version", capture_output=True, shell=True)
        [copilot_version] = re.findall(r"[0-9.]+", response.stdout.decode("utf8"))
    except ValueError:
        pass

    return Versions(parse_version(copilot_version), get_github_released_version("aws/copilot-cli"))


def get_aws_versions() -> Versions:
    aws_version = None
    try:
        response = subprocess.run("aws --version", capture_output=True, shell=True)
        matched = re.match(r"aws-cli/([0-9.]+)", response.stdout.decode("utf8"))
        aws_version = parse_version(matched.group(1))
    except ValueError:
        pass

    return Versions(aws_version, get_github_released_version("aws/aws-cli", True))


def get_github_released_version(repository: str, tags: bool = False) -> Tuple[int, int, int]:
    if tags:
        tags_list = requests.get(f"https://api.github.com/repos/{repository}/tags").json()
        versions = [parse_version(v["name"]) for v in tags_list]
        versions.sort(reverse=True)
        return versions[0]

    package_info = requests.get(f"https://api.github.com/repos/{repository}/releases/latest").json()
    return parse_version(package_info["tag_name"])


def _get_latest_release():
    package_info = requests.get("https://pypi.org/pypi/dbt-platform-helper/json").json()
    released_versions = package_info["releases"].keys()
    parsed_released_versions = [parse_version(v) for v in released_versions]
    parsed_released_versions.sort(reverse=True)
    return parsed_released_versions[0]


def get_platform_helper_versions(include_project_versions=True) -> PlatformHelperVersions:
    try:
        locally_installed_version = parse_version(version("dbt-platform-helper"))
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
        parse_version(deprecated_version_file.read_text())
        if deprecated_version_file.exists()
        else None
    )

    platform_config_default, pipeline_overrides = None, {}

    platform_config = load_unvalidated_config_file()

    if platform_config:
        platform_config_default = parse_version(
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


def _process_version_file_warnings(versions: PlatformHelperVersions):
    messages = []
    missing_default_version_message = f"Create a section in the root of '{PLATFORM_CONFIG_FILE}':\n\ndefault_versions:\n  platform-helper: "
    deprecation_message = f"Please delete '{PLATFORM_HELPER_VERSION_FILE}' as it is now deprecated."

    if versions.platform_config_default and versions.platform_helper_file_version:
        messages.append(deprecation_message)

    if versions.platform_config_default and not versions.platform_helper_file_version:
        return

    if not versions.platform_config_default and versions.platform_helper_file_version:
        messages.append(deprecation_message)
        messages.append(
            f"{missing_default_version_message}{string_version(versions.platform_helper_file_version)}\n"
        )

    if not versions.platform_config_default and not versions.platform_helper_file_version:
        message = f"Cannot get dbt-platform-helper version from '{PLATFORM_CONFIG_FILE}'.\n"
        message += f"{missing_default_version_message}{string_version(versions.local_version)}\n"
        click.secho(message, fg="red")

    if messages:
        click.secho("\n".join(messages), fg="yellow")


def validate_version_compatibility(
    app_version: Tuple[int, int, int], check_version: Tuple[int, int, int]
):
    app_major, app_minor, app_patch = app_version
    check_major, check_minor, check_patch = check_version
    app_version_as_string = string_version(app_version)
    check_version_as_string = string_version(check_version)

    if (app_major == 0 and check_major == 0) and (
        app_minor != check_minor or app_patch != check_patch
    ):
        raise IncompatibleMajorVersion(app_version_as_string, check_version_as_string)

    if app_major != check_major:
        raise IncompatibleMajorVersion(app_version_as_string, check_version_as_string)

    if app_minor != check_minor:
        raise IncompatibleMinorVersion(app_version_as_string, check_version_as_string)


def check_version_on_file_compatibility(
    app_version: Tuple[int, int, int], file_version: Tuple[int, int, int]
):
    app_major, app_minor, app_patch = app_version
    file_major, file_minor, file_patch = file_version

    return app_major == file_major and app_minor == file_minor and app_patch == file_patch


def get_template_generated_with_version(template_file_path: str) -> Tuple[int, int, int]:
    try:
        template_contents = Path(template_file_path).read_text()
        template_version = re.match(
            r"# Generated by platform-helper ([v.\-0-9]+)", template_contents
        ).group(1)
        return parse_version(template_version)
    except (IndexError, AttributeError):
        raise ValidationException(f"Template {template_file_path} has no version information")


def validate_template_version(app_version: Tuple[int, int, int], template_file_path: str):
    validate_version_compatibility(
        app_version,
        get_template_generated_with_version(template_file_path),
    )


def check_platform_helper_version_needs_update():
    if not running_as_installed_package() or "PLATFORM_TOOLS_SKIP_VERSION_CHECK" in os.environ:
        return

    versions = get_platform_helper_versions(include_project_versions=False)
    local_version = versions.local_version
    latest_release = versions.latest_release
    message = (
        f"You are running platform-helper v{string_version(local_version)}, upgrade to "
        f"v{string_version(latest_release)} by running run `pip install "
        "--upgrade dbt-platform-helper`."
    )
    try:
        validate_version_compatibility(local_version, latest_release)
    except IncompatibleMajorVersion:
        click.secho(message, fg="red")
    except IncompatibleMinorVersion:
        click.secho(message, fg="yellow")


def check_platform_helper_version_mismatch():
    if not running_as_installed_package():
        return

    versions = get_platform_helper_versions()
    local_version = versions.local_version
    platform_helper_file_version = parse_version(
        get_required_platform_helper_version(versions=versions)
    )

    if not check_version_on_file_compatibility(local_version, platform_helper_file_version):
        message = (
            f"WARNING: You are running platform-helper v{string_version(local_version)} against "
            f"v{string_version(platform_helper_file_version)} specified by {PLATFORM_HELPER_VERSION_FILE}."
        )
        click.secho(message, fg="red")


def running_as_installed_package():
    return "site-packages" in __file__


def get_required_platform_helper_version(
    pipeline: str = None, versions: PlatformHelperVersions = None
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
        string_version(v) if isinstance(v, tuple) else v for v in version_precedence if v
    ]

    out = non_null_version_precedence[0] if non_null_version_precedence else None

    if not out:
        raise SystemExit(1)

    return out
