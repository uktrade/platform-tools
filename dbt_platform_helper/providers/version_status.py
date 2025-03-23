from dataclasses import dataclass
from dataclasses import field
from typing import Dict
from typing import Optional

from dbt_platform_helper.constants import PLATFORM_CONFIG_FILE
from dbt_platform_helper.constants import PLATFORM_HELPER_VERSION_FILE
from dbt_platform_helper.providers.semantic_version import SemanticVersion


@dataclass
class VersionStatus:
    installed: SemanticVersion = None
    latest: SemanticVersion = None

    def __str__(self):
        attrs = {
            key: value for key, value in vars(self).items() if isinstance(value, SemanticVersion)
        }
        attrs_str = ", ".join(f"{key}: {value}" for key, value in attrs.items())
        return f"{self.__class__.__name__}: {attrs_str}"

    def is_outdated(self):
        return self.installed != self.latest

    def validate(self):
        pass


@dataclass
class PlatformHelperVersionStatus(VersionStatus):
    installed: Optional[SemanticVersion] = None
    latest: Optional[SemanticVersion] = None
    deprecated_version_file: Optional[SemanticVersion] = None
    platform_config_default: Optional[SemanticVersion] = None
    pipeline_overrides: Optional[Dict[str, str]] = field(default_factory=dict)

    def __str__(self):
        semantic_version_attrs = {
            key: value for key, value in vars(self).items() if isinstance(value, SemanticVersion)
        }

        class_str = ", ".join(f"{key}: {value}" for key, value in semantic_version_attrs.items())

        if self.pipeline_overrides.items():
            pipeline_overrides_str = "pipeline_overrides: " + ", ".join(
                f"{key}: {value}" for key, value in self.pipeline_overrides.items()
            )
            class_str = ", ".join([class_str, pipeline_overrides_str])

        return f"{self.__class__.__name__}: {class_str}"

    def validate(self) -> dict:
        if self.platform_config_default and not self.deprecated_version_file:
            return {}

        warnings = []
        errors = []

        missing_default_version_message = f"Create a section in the root of '{PLATFORM_CONFIG_FILE}':\n\ndefault_versions:\n  platform-helper: "
        deprecation_message = (
            f"Please delete '{PLATFORM_HELPER_VERSION_FILE}' as it is now deprecated."
        )

        if self.platform_config_default and self.deprecated_version_file:
            warnings.append(deprecation_message)

        if not self.platform_config_default and self.deprecated_version_file:
            warnings.append(deprecation_message)
            warnings.append(f"{missing_default_version_message}{self.deprecated_version_file}\n")

        if not self.platform_config_default and not self.deprecated_version_file:
            message = f"Cannot get dbt-platform-helper version from '{PLATFORM_CONFIG_FILE}'.\n"
            message += f"{missing_default_version_message}{self.installed}\n"
            errors.append(message)

        return {
            "warnings": warnings,
            "errors": errors,
        }
