from dbt_platform_helper.platform_exception import PlatformException


class AWSException(PlatformException):
    pass


class CreateTaskTimeoutError(AWSException):
    def __init__(self, addon_name: str, application_name: str, environment: str):
        super().__init__(
            f"""Client ({addon_name}) ECS task has failed to start for "{application_name}" in "{environment}" environment."""
        )


class ImageNotFoundError(AWSException):
    def __init__(self, commit: str):
        super().__init__(
            f"""The commit hash "{commit}" has not been built into an image, try the `platform-helper codebase build` command first."""
        )


class ResourceNotFoundException(AWSException):
    pass


# Todo: This should probably be in the AWS Copilot provider, but was causing circular import when we tried it pre refactoring the utils/aws.py
class CopilotCodebaseNotFoundError(PlatformException):
    def __init__(self, codebase: str):
        super().__init__(
            f"""The codebase "{codebase}" either does not exist or has not been deployed."""
        )
