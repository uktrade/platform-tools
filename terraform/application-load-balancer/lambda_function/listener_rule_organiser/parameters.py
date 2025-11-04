from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DeploymentMode(Enum):
    PLATFORM = "platform"
    COPILOT = "copilot"
    DUAL_DEPLOY_PLATFORM = "dual-deploy-platform-traffic"
    DUAL_DEPLOY_COPILOT = "dual-deploy-copilot-traffic"


class LifecycleAction(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class Lifecycle:
    action: LifecycleAction
    prev_input: 'Parameters'

    def __post_init__(self):
        # Convert string to enum if needed
        if isinstance(self.action, str):
            self.action = LifecycleAction(self.action)
        # Convert dict to Parameters if needed
        if isinstance(self.prev_input, dict):
            self.prev_input = Parameters(**self.prev_input)

    def __eq__(self, other):
        if not isinstance(other, Lifecycle):
            return False

        return (
                self.action == other.action
                and self.prev_input == other.prev_input
        )


@dataclass(eq=False)
class Parameters:
    service_name: str
    target_group: str
    deployment_mode: Optional[DeploymentMode] = None
    lifecycle: Optional[Lifecycle] = None

    def __post_init__(self):
        # Convert dict to Lifecycle if needed
        if isinstance(self.lifecycle, dict):
            self.lifecycle = Lifecycle(**self.lifecycle)
        if isinstance(self.deployment_mode, str):
            self.deployment_mode = DeploymentMode(self.deployment_mode)

    def has_changes(self):
        if self.lifecycle is None:
            return True

        return (
            self.service_name != self.lifecycle.prev_input.service_name
            or self.target_group != self.lifecycle.prev_input.target_group
            or self.deployment_mode != self.lifecycle.prev_input.deployment_mode
        )

    def __eq__(self, other):
        if not isinstance(other, Parameters):
            return False

        return (
                self.service_name == other.service_name
                and self.target_group == other.target_group
                and self.deployment_mode == other.deployment_mode
                and self.lifecycle == other.lifecycle
        )
