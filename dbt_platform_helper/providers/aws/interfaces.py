from abc import ABC
from abc import abstractmethod


class ClientProvider(ABC):

    def __init__(self, client):
        self.client = client
        self.engine = None

    @abstractmethod
    def get_reference(self):
        raise NotImplementedError()

    @abstractmethod
    def get_supported_versions(self):
        raise NotImplementedError()
