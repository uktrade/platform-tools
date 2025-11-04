from dataclasses import dataclass
from enum import Enum
from typing import Optional


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
    lifecycle: Optional[Lifecycle] = None

    def __post_init__(self):
        # Convert dict to Lifecycle if needed
        if isinstance(self.lifecycle, dict):
            self.lifecycle = Lifecycle(**self.lifecycle)

    def has_changes(self):
        if self.lifecycle is None:
            return True

        return (
                self.service_name != self.lifecycle.prev_input.service_name
                or self.target_group != self.lifecycle.prev_input.target_group
        )

    def __eq__(self, other):
        if not isinstance(other, Parameters):
            return False

        return (
                self.service_name == other.service_name
                and self.target_group == other.target_group
                and self.lifecycle == other.lifecycle
        )
