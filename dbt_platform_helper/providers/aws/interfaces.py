from typing import Protocol


class GetVersionsProtocol(Protocol):
    def __get_support_versions__(self) -> list[str]: ...


class GetReferenceProtocal(Protocol):
    def __get_reference__(self) -> str: ...
