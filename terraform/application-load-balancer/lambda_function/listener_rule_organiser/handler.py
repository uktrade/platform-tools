import os
from enum import Enum

from dummy_rule_manager import DummyRuleManager


class LifecycleAction(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class Lifecycle:
    def __init__(self, lifecycle):
        self.action = LifecycleAction(lifecycle["action"])
        if lifecycle["prev_input"] is not None:
            self.previous = Parameters(
                lifecycle["prev_input"]["ServiceName"],
                lifecycle["prev_input"]["TargetGroup"],
            )


class Parameters:
    def __init__(self, service_name, target_group, lifecycle=None):
        self.service_name = service_name
        self.target_group = target_group
        if lifecycle is not None:
            self.lifecycle = Lifecycle(lifecycle)


def handler(event, context):
    organiser = DummyRuleManager(
        application=os.environ["APPLICATION"],
        environment=os.environ["ENVIRONMENT"],
        listener_arn=os.environ["LISTENER_ARN"],
    )

    parameters = Parameters(event["ServiceName"], event["TargetGroup"], event["Lifecycle"])

    match parameters.lifecycle.action:
        case LifecycleAction.CREATE:
            organiser.create_dummy_rule(parameters.target_group, parameters.service_name)
        case LifecycleAction.UPDATE:
            if (
                parameters.target_group != parameters.lifecycle.previous.target_group
                or parameters.service_name != parameters.lifecycle.previous.service_name
            ):
                organiser.delete_dummy_rule(parameters.lifecycle.previous.service_name)
                organiser.create_dummy_rule(parameters.target_group, parameters.service_name)
        case LifecycleAction.DELETE:
            organiser.delete_dummy_rule(parameters.lifecycle.previous.service_name)
        case _:
            raise Exception("Unexpected lifecycle action")

    return {
        "statusCode": 200,
        "message": f"dummy rule {parameters.lifecycle.action.value} was successful",
    }
