from pathlib import Path

from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.yaml_file import YamlFileProvider


class NoDeploymentRepoConfigException(PlatformException):
    def __init__(self):
        super().__init__("Could not find a deployment repository, no checks to run.")


class Config:

    def __init__(
        self,
        io: ClickIOProvider = ClickIOProvider(),
        platform_helper_versioning_domain: PlatformHelperVersioning = PlatformHelperVersioning(
            version_file_version_provider=YamlFileProvider  # Overrides DeprecatedVersionFileVersionProvider wrapper
        ),
    ):
        self.io = io
        self.platform_helper_versioning_domain = platform_helper_versioning_domain

    def validate(self):
        if Path("copilot").exists():
            self.io.debug("\nDetected a deployment repository\n")
            platform_helper_version_status = (
                self.platform_helper_versioning_domain._get_version_status(
                    include_project_versions=True
                )
            )
            self.io.process_messages(platform_helper_version_status.validate())
        else:
            raise NoDeploymentRepoConfigException()

    def generate_aws(self):
        pass
