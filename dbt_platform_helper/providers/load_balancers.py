import boto3

from dbt_platform_helper.platform_exception import PlatformException

# TODO - a good candidate for a dataclass when this is refactored into a class.
# Below methods should also really be refactored to not be so tightly coupled with eachother.


def get_load_balancer_for_application(session: boto3.Session, app: str, env: str) -> str:
    lb_client = session.client("elbv2")

    describe_response = lb_client.describe_load_balancers()
    load_balancers = [lb["LoadBalancerArn"] for lb in describe_response["LoadBalancers"]]

    load_balancers = lb_client.describe_tags(ResourceArns=load_balancers)["TagDescriptions"]

    load_balancer_arn = None
    for lb in load_balancers:
        tags = {t["Key"]: t["Value"] for t in lb["Tags"]}
        if tags.get("copilot-application") == app and tags.get("copilot-environment") == env:
            load_balancer_arn = lb["ResourceArn"]

    if not load_balancer_arn:
        raise LoadBalancerNotFoundException(
            f"No load balancer found for {app} in the {env} environment"
        )

    return load_balancer_arn


def get_https_listener_for_application(session: boto3.Session, app: str, env: str) -> str:
    load_balancer_arn = get_load_balancer_for_application(session, app, env)
    lb_client = session.client("elbv2")
    listeners = lb_client.describe_listeners(LoadBalancerArn=load_balancer_arn)["Listeners"]

    listener_arn = None

    try:
        listener_arn = next(l["ListenerArn"] for l in listeners if l["Protocol"] == "HTTPS")
    except StopIteration:
        pass

    if not listener_arn:
        raise ListenerNotFoundException(f"No HTTPS listener for {app} in the {env} environment")

    return listener_arn


def get_https_certificate_for_application(session: boto3.Session, app: str, env: str) -> str:

    listener_arn = get_https_listener_for_application(session, app, env)
    cert_client = session.client("elbv2")
    certificates = cert_client.describe_listener_certificates(ListenerArn=listener_arn)[
        "Certificates"
    ]

    try:
        certificate_arn = next(c["CertificateArn"] for c in certificates if c["IsDefault"])
    except StopIteration:
        raise CertificateNotFoundException(env)

    return certificate_arn


class LoadBalancerException(PlatformException):
    pass


class LoadBalancerNotFoundException(LoadBalancerException):
    pass


class ListenerNotFoundException(LoadBalancerException):
    pass


class ListenerRuleNotFoundException(LoadBalancerException):
    pass


class CertificateNotFoundException(PlatformException):
    def __init__(self, environment_name: str):
        super().__init__(
            f"""No certificate found with domain name matching environment {environment_name}."."""
        )
