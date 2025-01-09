from typing import Protocol


class GetVersionsProtocol(Protocol):
    def __get_supported_versions__(self) -> list[str]: ...


class GetReferenceProtocol(Protocol):
    def __get_reference__(self) -> str: ...
