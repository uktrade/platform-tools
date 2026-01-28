from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List
from typing import Optional


@dataclass
class DeployedService:
    name: str
    tag: str
    environment: str


class PipelineStatus(Enum):
    IN_PROGRESS = "InProgress"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    STOPPED = "Stopped"
    STOPPING = "Stopping"
    SUPERSEDED = "Superseded"


@dataclass
class PipelineExecution:
    execution_id: str
    status: PipelineStatus
    name: str

    @property
    def is_complete(self) -> bool:
        return self.status in [
            PipelineStatus.SUCCEEDED,
            PipelineStatus.FAILED,
            PipelineStatus.STOPPED,
            PipelineStatus.SUPERSEDED,
        ]

    def is_successful(self) -> bool:
        return self.status == PipelineStatus.SUCCEEDED


@dataclass
class PipelineDetails:
    name: str
    image_tag: str
    environment: Optional[str] = None


class DeploymentPort(ABC):

    @abstractmethod
    def get_deployed_services(
        self, application: str, environment: str, platform: bool = True
    ) -> List[DeployedService]:
        pass


class PipelinePort(ABC):
    @abstractmethod
    def trigger_deployment(self, details: PipelineDetails) -> Optional[str]:
        pass

    # def get_pipeline_url():
    @abstractmethod
    def get_execution_status(self, pipeline_name, execution_id) -> Optional[PipelineExecution]:
        pass

    @abstractmethod
    def pipeline_exists(self, pipeline_name: str) -> bool:
        pass
