from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.platform_helper_versioning import (
    PlatformHelperVersioning,
)
from dbt_platform_helper.providers.semantic_version import PlatformHelperVersionStatus
from dbt_platform_helper.providers.semantic_version import SemanticVersion
from dbt_platform_helper.utils.versioning import running_as_installed_package


class PlatformHelperVersionNotFoundException(PlatformException):
    def __init__(self):
        super().__init__(f"""Platform helper version could not be resolved.""")


class RequiredVersion:
    def __init__(self, io=None, platform_helper_versioning=None):
        self.io = io or ClickIOProvider()
        self.platform_helper_versioning = platform_helper_versioning or PlatformHelperVersioning(
            io=self.io
        )

    def get_required_platform_helper_version(
        self, pipeline: str = None, version_status: PlatformHelperVersionStatus = None
    ) -> str:
        pipeline_version = version_status.pipeline_overrides.get(pipeline)
        version_precedence = [
            pipeline_version,
            version_status.platform_config_default,
            version_status.deprecated_version_file,
        ]
        non_null_version_precedence = [
            f"{v}" if isinstance(v, SemanticVersion) else v for v in version_precedence if v
        ]

        out = non_null_version_precedence[0] if non_null_version_precedence else None

        if not out:
            raise PlatformHelperVersionNotFoundException

        return out

    def get_required_version(self, pipeline=None):
        version_status = self.platform_helper_versioning.get_status()
        self.io.process_messages(version_status.validate())
        required_version = self.get_required_platform_helper_version(pipeline, version_status)
        self.io.info(required_version)
        return required_version

    # Used in the generate command
    def check_platform_helper_version_mismatch(self):
        if not running_as_installed_package():
            return

        version_status = self.platform_helper_versioning.get_status()
        self.io.process_messages(version_status.validate())

        required_version = SemanticVersion.from_string(
            self.get_required_platform_helper_version(version_status=version_status)
        )

        if not version_status.local == required_version:
            message = (
                f"WARNING: You are running platform-helper v{version_status.local} against "
                f"v{required_version} specified for the project."
            )
            self.io.warn(message)
