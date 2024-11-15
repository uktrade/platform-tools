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
