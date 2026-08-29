from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Dict


class ConfigPort(ABC):

    @abstractmethod
    def load_unvalidated_config_file(self, path: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_enriched_config(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def load_and_validate_platform_config(self, path: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def config_file_check(self, path: str):
        pass

    @staticmethod
    def apply_environment_defaults(config: Dict) -> Dict[str, Any]:
        pass

    @abstractmethod
    def write_platform_config(self, new_platform_config: Dict):
        pass
