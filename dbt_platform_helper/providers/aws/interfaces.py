from typing import Protocol


class GetVersionsProtocol(Protocol):
    def get_supported_versions(self) -> list[str]: ...


class GetReferenceProtocol(Protocol):
    def get_reference(self) -> str: ...


class AwsGetVersionProtocol(GetReferenceProtocol, GetVersionsProtocol):
    pass
