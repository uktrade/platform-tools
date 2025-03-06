from pathlib import Path

from dbt_platform_helper.platform_exception import PlatformException


class NoDeploymentRepoConfigException(PlatformException):
    def __init__(self):
        super().__init__("Could not find a deployment repository, no checks to run.")


class Config:

    def __init__(self):
        pass

    def validate(self):
        if Path("copilot").exists():
            pass
        else:
            raise NoDeploymentRepoConfigException()

    def generate_aws(self):
        pass
