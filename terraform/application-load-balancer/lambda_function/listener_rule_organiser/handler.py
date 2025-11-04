import os
from dummy_rule_manager import DummyRuleManager
from parameters import Parameters
from parameters import LifecycleAction


def handler(event, context):
    parameters = Parameters(**event)

    rule_manager = DummyRuleManager(
        application=os.environ["APPLICATION"],
        environment=os.environ["ENVIRONMENT"],
        listener_arn=os.environ["LISTENER_ARN"],
    )

    match parameters.lifecycle.action:
        case LifecycleAction.CREATE:
            print('creating')
            rule_manager.create_rules(parameters)
        case LifecycleAction.UPDATE:
            if parameters.has_changes():
                print('updating')
                rule_manager.delete_rules(parameters)
                rule_manager.create_rules(parameters)
        case LifecycleAction.DELETE:
            print('deleting')
            rule_manager.delete_rules(parameters)
        case _:
            raise Exception("Unexpected lifecycle action")

    return {
        "statusCode": 200,
        "message": f"dummy rule {parameters.lifecycle.action.value} was successful",
    }
