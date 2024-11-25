from dbt_platform_helper.constants import CONDUIT_ADDON_TYPES


class ValidationException(Exception):
    pass


class AWSException(Exception):
    pass


class IncompatibleMajorVersion(ValidationException):
    def __init__(self, app_version: str, check_version: str):
        super().__init__()
        self.app_version = app_version
        self.check_version = check_version


class IncompatibleMinorVersion(ValidationException):
    def __init__(self, app_version: str, check_version: str):
        super().__init__()
        self.app_version = app_version
        self.check_version = check_version


class NoClusterError(AWSException):
    def __init__(self, application_name: str, environment: str):
        super().__init__(
            f"""No ECS cluster found for "{application_name}" in "{environment}" environment."""
        )


class CreateTaskTimeoutError(AWSException):
    def __init__(self, addon_name: str, application_name: str, environment: str):
        super().__init__(
            f"""Client ({addon_name}) ECS task has failed to start for "{application_name}" in "{environment}" environment."""
        )


class ParameterNotFoundError(AWSException):
    def __init__(self, application_name: str, environment: str):
        super().__init__(
            f"""No parameter called "/copilot/applications/{application_name}/environments/{environment}/addons". Try deploying the "{application_name}" "{environment}" environment."""
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
            f"""The configuration for the addon {addon_name}, is missconfigured and missing the addon type."""
        )


class CopilotCodebaseNotFoundError(Exception):
    pass


class NotInCodeBaseRepositoryError(Exception):
    pass


class NoCopilotCodebasesFoundError(Exception):
    pass


class ImageNotFoundError(Exception):
    pass


class ApplicationDeploymentNotTriggered(Exception):
    pass


class ApplicationNotFoundError(Exception):
    pass


class ApplicationEnvironmentNotFoundError(Exception):
    pass


class SecretNotFoundError(AWSException):
    # application_name: str, environment: str,
    def __init__(self, secret_name: str):
        # super().__init__(f"""No secret called "{secret_name}" for "{application_name}" in "{environment}" environment.""")
        super().__init__(f"""No secret called "{secret_name}".""")


class ECSAgentNotRunning(AWSException):
    pass
