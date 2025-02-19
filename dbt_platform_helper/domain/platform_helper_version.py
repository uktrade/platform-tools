import os

from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.semantic_version import (
    IncompatibleMajorVersionException,
)
from dbt_platform_helper.providers.semantic_version import (
    IncompatibleMinorVersionException,
)
from dbt_platform_helper.utils.versioning import get_platform_helper_version_status
from dbt_platform_helper.utils.versioning import running_as_installed_package


class PlatformHelperVersion:
    def __init__(self, io: ClickIOProvider = ClickIOProvider()):
        self.io = io

    def get_status():
        pass

    def check_if_needs_update(self):
        if not running_as_installed_package() or "PLATFORM_TOOLS_SKIP_VERSION_CHECK" in os.environ:
            return

        version_status = get_platform_helper_version_status(include_project_versions=False)
        self.io.process_messages(version_status.warn())

        message = (
            f"You are running platform-helper v{version_status.local}, upgrade to "
            f"v{version_status.latest} by running run `pip install "
            "--upgrade dbt-platform-helper`."
        )

        try:
            version_status.local.validate_compatibility_with(version_status.latest)
        except IncompatibleMajorVersionException:
            self.io.error(message)
        except IncompatibleMinorVersionException:
            self.io.warn(message)
