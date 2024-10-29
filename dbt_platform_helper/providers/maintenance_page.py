from dbt_platform_helper.commands.environment import offline_command
from dbt_platform_helper.commands.environment import online_command


class MaintenancePageProvider:
    def __init__(self):
        self.offline = offline_command
        self.online = online_command


#     def offline_command(self, app, env, svc, template, vpc):
#         application = get_application(app)
#         application_environment = get_app_environment(app, env)
#
#         if "*" in svc:
#             services = [
#                 s for s in application.services.values() if s.kind == "Load Balanced Web Service"
#             ]
#         else:
#             all_services = [get_app_service(app, s) for s in list(svc)]
#             services = [s for s in all_services if s.kind == "Load Balanced Web Service"]
#
#         if not services:
#             click.secho(f"No services deployed yet to {app} environment {env}", fg="red")
#             raise click.Abort
#
#         try:
#             https_listener = find_https_listener(application_environment.session, app, env)
#             current_maintenance_page = get_maintenance_page(
#                 application_environment.session, https_listener
#             )
#             remove_current_maintenance_page = False
#             if current_maintenance_page:
#                 remove_current_maintenance_page = click.confirm(
#                     f"There is currently a '{current_maintenance_page}' maintenance page for the {env} "
#                     f"environment in {app}.\nWould you like to replace it with a '{template}' "
#                     f"maintenance page?"
#                 )
#                 if not remove_current_maintenance_page:
#                     raise click.Abort
#
#             if remove_current_maintenance_page or click.confirm(
#                 f"You are about to enable the '{template}' maintenance page for the {env} "
#                 f"environment in {app}.\nWould you like to continue?"
#             ):
#                 if current_maintenance_page and remove_current_maintenance_page:
#                     remove_maintenance_page(application_environment.session, https_listener)
#
#                 allowed_ips = get_env_ips(vpc, application_environment)
#
#                 add_maintenance_page(
#                     application_environment.session,
#                     https_listener,
#                     app,
#                     env,
#                     services,
#                     allowed_ips,
#                     template,
#                 )
#                 click.secho(
#                     f"Maintenance page '{template}' added for environment {env} in application {app}",
#                     fg="green",
#                 )
#             else:
#                 raise click.Abort
#
#         except LoadBalancerNotFoundError:
#             click.secho(
#                 f"No load balancer found for environment {env} in the application {app}.", fg="red"
#             )
#             raise click.Abort
#
#         except ListenerNotFoundError:
#             click.secho(
#                 f"No HTTPS listener found for environment {env} in the application {app}.", fg="red"
#             )
#             raise click.Abort
#
#
# def get_application(app_name: str):
#     return load_application(app_name)
#
#
# def get_app_environment(app_name: str, env_name: str) -> Environment:
#     application = get_application(app_name)
#     application_environment = application.environments.get(env_name)
#
#     if not application_environment:
#         click.secho(
#             f"The environment {env_name} was not found in the application {app_name}. "
#             f"It either does not exist, or has not been deployed.",
#             fg="red",
#         )
#         raise click.Abort
#
#     return application_environment
#
#
# def get_app_service(app_name: str, svc_name: str) -> Service:
#     application = get_application(app_name)
#     application_service = application.services.get(svc_name)
#
#     if not application_service:
#         click.secho(
#             f"The service {svc_name} was not found in the application {app_name}. "
#             f"It either does not exist, or has not been deployed.",
#             fg="red",
#         )
#         raise click.Abort
#
#     return application_service
#
#
# def get_listener_rule_by_tag(elbv2_client, listener_arn, tag_key, tag_value):
#     response = elbv2_client.describe_rules(ListenerArn=listener_arn)
#     for rule in response["Rules"]:
#         rule_arn = rule["RuleArn"]
#
#         tags_response = elbv2_client.describe_tags(ResourceArns=[rule_arn])
#         for tag_description in tags_response["TagDescriptions"]:
#             for tag in tag_description["Tags"]:
#                 if tag["Key"] == tag_key and tag["Value"] == tag_value:
#                     return rule
#
#
# def get_vpc_id(session, env_name, vpc_name=None):
#     if not vpc_name:
#         vpc_name = f"{session.profile_name}-{env_name}"
#
#     filters = [{"Name": "tag:Name", "Values": [vpc_name]}]
#     vpcs = session.client("ec2").describe_vpcs(Filters=filters)["Vpcs"]
#
#     if not vpcs:
#         filters[0]["Values"] = [session.profile_name]
#         vpcs = session.client("ec2").describe_vpcs(Filters=filters)["Vpcs"]
#
#     if not vpcs:
#         click.secho(
#             f"No VPC found with name {vpc_name} in AWS account {session.profile_name}.", fg="red"
#         )
#         raise click.Abort
#
#     return vpcs[0]["VpcId"]
#
#
# def get_subnet_ids(session, vpc_id):
#     subnets = session.client("ec2").describe_subnets(
#         Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
#     )["Subnets"]
#
#     if not subnets:
#         click.secho(f"No subnets found for VPC with id: {vpc_id}.", fg="red")
#         raise click.Abort
#
#     public_tag = {"Key": "subnet_type", "Value": "public"}
#     public = [subnet["SubnetId"] for subnet in subnets if public_tag in subnet["Tags"]]
#     private_tag = {"Key": "subnet_type", "Value": "private"}
#     private = [subnet["SubnetId"] for subnet in subnets if private_tag in subnet["Tags"]]
#
#     return public, private
#
#
# def get_cert_arn(session, application, env_name):
#     try:
#         arn = find_https_certificate(session, application, env_name)
#     except:
#         click.secho(
#             f"No certificate found with domain name matching environment {env_name}.", fg="red"
#         )
#         raise click.Abort
#
#     return arn
#
#
# def get_env_ips(vpc: str, application_environment: Environment) -> List[str]:
#     account_name = f"{application_environment.session.profile_name}"
#     vpc_name = vpc if vpc else account_name
#     ssm_client = application_environment.session.client("ssm")
#
#     try:
#         param_value = ssm_client.get_parameter(Name=f"/{vpc_name}/EGRESS_IPS")["Parameter"]["Value"]
#     except ssm_client.exceptions.ParameterNotFound:
#         click.secho(f"No parameter found with name: /{vpc_name}/EGRESS_IPS")
#         raise click.Abort
#
#     return [ip.strip() for ip in param_value.split(",")]
#
#
#
