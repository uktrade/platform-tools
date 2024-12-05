from dbt_platform_helper.platform_exception import PlatformException


class AWSException(PlatformException):
    pass


class CreateTaskTimeoutError(AWSException):
    def __init__(self, addon_name: str, application_name: str, environment: str):
        super().__init__(
            f"""Client ({addon_name}) ECS task has failed to start for "{application_name}" in "{environment}" environment."""
        )


class ResourceNotFoundException(AWSException):
    pass
