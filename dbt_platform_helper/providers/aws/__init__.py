from dbt_platform_helper.providers.aws.interfaces import GetReferenceProtocal
from dbt_platform_helper.providers.aws.interfaces import GetVersionsProtocol


def get_supported_versions(obj: GetVersionsProtocol) -> list[str]:
    if hasattr(obj, "__get_supported_versions__"):
        return obj.__get_supported_versions__()
    raise AttributeError(
        f"Object of type {type(obj).__name__} does not support get_supported_versions"
    )


def get_reference(obj: GetReferenceProtocal) -> str:
    if hasattr(obj, "__get_reference__"):
        return obj.__get_reference__()
    raise AttributeError(f"Object of type {type(obj).__name__} does not support get_reference")
