import os

from dbt_platform_helper.constants import CONDUIT_ADDON_TYPES
from dbt_platform_helper.platform_exception import PlatformException

# These exceptions will be moved during further refactoring work


class AWSException(PlatformException):
    pass


class ApplicationException(PlatformException):
    pass


# Todo: Move as part of the validation provider refactor
class ValidationException(Exception):
    pass


# Todo: Move as part of the validation provider refactor
class IncompatibleMajorVersion(ValidationException):
    def __init__(self, app_version: str, check_version: str):
        super().__init__()
        self.app_version = app_version
        self.check_version = check_version


# Todo: Move as part of the validation provider refactor
class IncompatibleMinorVersion(ValidationException):
    def __init__(self, app_version: str, check_version: str):
        super().__init__()
        self.app_version = app_version
        self.check_version = check_version


# Todo: Move as part of the copilot provider refactor
class CreateTaskTimeoutError(AWSException):
    def __init__(self, addon_name: str, application_name: str, environment: str):
        super().__init__(
            f"""Client ({addon_name}) ECS task has failed to start for "{application_name}" in "{environment}" environment."""
        )


class AddonNotFoundError(AWSException):
    def __init__(self, addon_name: str):
        super().__init__(f"""Addon "{addon_name}" does not exist.""")


class InvalidAddonTypeError(AWSException):
    def __init__(self, addon_type):
        self.addon_type = addon_type
        super().__init__(
            f"""Addon type "{self.addon_type}" is not supported, we support: {", ".join(CONDUIT_ADDON_TYPES)}."""
        )


class AddonTypeMissingFromConfigError(AWSException):
    def __init__(self, addon_name: str):
        super().__init__(
            f"""The configuration for the addon {addon_name}, is misconfigured and missing the addon type."""
        )


class CopilotCodebaseNotFoundError(PlatformException):
    def __init__(self, codebase: str):
        super().__init__(
            f"""The codebase "{codebase}" either does not exist or has not been deployed."""
        )


class NotInCodeBaseRepositoryError(PlatformException):
    def __init__(self):
        super().__init__(
            "You are in the deploy repository; make sure you are in the application codebase repository.",
        )


class NoCopilotCodebasesFoundError(PlatformException):
    def __init__(self, application_name: str):
        super().__init__(f"""No codebases found for application "{application_name}".""")


class ImageNotFoundError(PlatformException):
    def __init__(self, commit: str):
        super().__init__(
            f"""The commit hash "{commit}" has not been built into an image, try the `platform-helper codebase build` command first."""
        )


class ApplicationDeploymentNotTriggered(PlatformException):
    def __init__(self, codebase: str):
        super().__init__(f"""Your deployment for {codebase} was not triggered.""")


class ApplicationNotFoundError(ApplicationException):
    def __init__(self, application_name: str):
        super().__init__(
            f"""The account "{os.environ.get("AWS_PROFILE")}" does not contain the application "{application_name}"; ensure you have set the environment variable "AWS_PROFILE" correctly."""
        )


class ApplicationEnvironmentNotFoundError(ApplicationException):
    def __init__(self, environment: str):
        super().__init__(
            f"""The environment "{environment}" either does not exist or has not been deployed."""
        )


class ECSAgentNotRunning(AWSException):
    def __init__(self):
        super().__init__("""ECS exec agent never reached "RUNNING" status""")


class ResourceNotFoundException(AWSException):
    pass
