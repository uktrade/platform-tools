from dbt_platform_helper.platform_exception import PlatformException


class AWSException(PlatformException):
    pass


class CreateTaskTimeoutException(AWSException):
    def __init__(self, addon_name: str, application_name: str, environment: str):
        super().__init__(
            f"""Client ({addon_name}) ECS task has failed to start for "{application_name}" in "{environment}" environment."""
        )


class ImageNotFoundException(AWSException):
    def __init__(self, image_ref: str):
        super().__init__(
            f"""An image labelled "{image_ref}" could not be found in your image repository. Try the `platform-helper codebase build` command first."""
        )


class RepositoryNotFoundException(AWSException):
    def __init__(self, repository: str):
        super().__init__(f"""The ECR repository "{repository}" could not be found.""")


class LogGroupNotFoundException(AWSException):
    def __init__(self, log_group_name: str):
        super().__init__(f"""No log group called "{log_group_name}".""")


# TODO: DBTP-1976: This should probably be in the AWS Copilot provider, but was causing circular import when we tried it pre refactoring the utils/aws.py
class CopilotCodebaseNotFoundException(PlatformException):
    def __init__(self, codebase: str):
        super().__init__(
            f"""The codebase "{codebase}" either does not exist or has not been deployed."""
        )


class CreateAccessTokenException(AWSException):
    def __init__(self, client_id: str):
        super().__init__(f"""Failed to create access token for Client "{client_id}".""")


class UnableToRetrieveSSOAccountList(AWSException):
    def __init__(self):
        super().__init__("Unable to retrieve AWS SSO account list")
