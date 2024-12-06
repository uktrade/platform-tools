from dbt_platform_helper.platform_exception import PlatformException


class ValidationException(PlatformException):
    pass


class IncompatibleMajorVersionException(ValidationException):
    def __init__(self, app_version: str, check_version: str):
        super().__init__()
        self.app_version = app_version
        self.check_version = check_version


class IncompatibleMinorVersionException(ValidationException):
    def __init__(self, app_version: str, check_version: str):
        super().__init__()
        self.app_version = app_version
        self.check_version = check_version
