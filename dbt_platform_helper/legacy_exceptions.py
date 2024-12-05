from dbt_platform_helper.platform_exception import PlatformException

# These exceptions will be moved during further refactoring work


class AWSException(PlatformException):
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


# Todo: Move when refactoring utils/aws.py to provider(s)
class CopilotCodebaseNotFoundError(PlatformException):
    def __init__(self, codebase: str):
        super().__init__(
            f"""The codebase "{codebase}" either does not exist or has not been deployed."""
        )


# Todo: No longer in use, but referenced in th tests. Investigate.
class NoCopilotCodebasesFoundError(PlatformException):
    def __init__(self, application_name: str):
        super().__init__(f"""No codebases found for application "{application_name}".""")


# Todo: Move when refactoring utils/aws.py to provider(s)
class ImageNotFoundError(PlatformException):
    def __init__(self, commit: str):
        super().__init__(
            f"""The commit hash "{commit}" has not been built into an image, try the `platform-helper codebase build` command first."""
        )


# Todo: Move when refactoring utils/aws.py to provider(s)
class ResourceNotFoundException(AWSException):
    pass
