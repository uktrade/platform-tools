from dbt_platform_helper.platform_exception import PlatformException


class AWSException(PlatformException):
    pass


class CreateTaskTimeoutException(AWSException):
    def __init__(self, addon_name: str, application_name: str, environment: str):
        super().__init__(
            f"""Client ({addon_name}) ECS task has failed to start for "{application_name}" in "{environment}" environment."""
        )


class ImageNotFoundException(AWSException):
    def __init__(self, commit: str):
        super().__init__(
            f"""The commit hash "{commit}" has not been built into an image, try the `platform-helper codebase build` command first."""
        )


class RepositoryNotFoundException(AWSException):
    def __init__(self, repository: str):
        super().__init__(f"""The ECR repository "{repository}" could not be found.""")


class LogGroupNotFoundException(AWSException):
    def __init__(self, log_group_name: str):
        super().__init__(f"""No log group called "{log_group_name}".""")


class CreateAccessTokenException(AWSException):
    def __init__(self, client_id: str):
        super().__init__(f"""Failed to create access token for Client "{client_id}".""")


class UnableToRetrieveSSOAccountList(AWSException):
    def __init__(self):
        super().__init__("Unable to retrieve AWS SSO account list")
