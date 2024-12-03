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
    pass


class CreateTaskTimeoutError(AWSException):
    pass


class ParameterNotFoundError(AWSException):
    pass


class AddonNotFoundError(AWSException):
    pass


class InvalidAddonTypeError(AWSException):
    def __init__(self, addon_type):
        self.addon_type = addon_type


class AddonTypeMissingFromConfigError(AWSException):
    pass


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
    pass


class ECSAgentNotRunning(AWSException):
    pass


class ResourceNotFoundException(AWSException):
    pass
