from pathlib import Path

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider


class NoDeploymentRepoConfigException(PlatformException):
    def __init__(self):
        super().__init__("Could not find a deployment repository, no checks to run.")


class Config:

    def __init__(self, io: ClickIOProvider = ClickIOProvider()):
        self.io = io

    def validate(self):
        if Path("copilot").exists():
            self.io.debug("\nDetected a deployment repository")
        else:
            raise NoDeploymentRepoConfigException()

    def generate_aws(self):
        pass
