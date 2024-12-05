from dbt_platform_helper.platform_exception import PlatformException

# These exceptions will be moved during further refactoring work


# Todo: Move when ???
class CopilotCodebaseNotFoundError(PlatformException):
    def __init__(self, codebase: str):
        super().__init__(
            f"""The codebase "{codebase}" either does not exist or has not been deployed."""
        )


# Todo: Move when refactoring utils/aws.py to provider(s)
class ImageNotFoundError(PlatformException):
    def __init__(self, commit: str):
        super().__init__(
            f"""The commit hash "{commit}" has not been built into an image, try the `platform-helper codebase build` command first."""
        )
