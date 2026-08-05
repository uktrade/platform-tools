from abc import ABC
from abc import abstractmethod
from pathlib import Path


class FileSystemPort(ABC):

    @abstractmethod
    def get_current_directory(self) -> Path:
        pass
