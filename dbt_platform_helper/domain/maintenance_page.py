import itertools
import random
import re
import string
import traceback
from pathlib import Path
from typing import Callable
from typing import List
from typing import Union

import click

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.load_balancers import ListenerNotFoundException
from dbt_platform_helper.providers.load_balancers import ListenerRuleNotFoundException
from dbt_platform_helper.providers.load_balancers import LoadBalancerNotFoundException
from dbt_platform_helper.providers.load_balancers import LoadBalancerProvider
from dbt_platform_helper.utils.application import Application
from dbt_platform_helper.utils.application import Environment
from dbt_platform_helper.utils.application import Service


class MaintenancePageException(PlatformException):
    pass


class LoadBalancedWebServiceNotFoundException(MaintenancePageException):
    def __init__(self, application_name: str):
        super().__init__(f"No services deployed yet to {application_name} ")


class FailedToActivateMaintenancePageException(MaintenancePageException):
    def __init__(
        self,
        application_name: str,
        env: str,
        original_exception: Exception,
        rolled_back_rules: dict[str, bool] = {},
    ):
        super().__init__(
            f"Maintenance page failed to activate for the {application_name} application in environment {env}."
        )
        self.orginal_exception = original_exception
        self.rolled_back_rules = rolled_back_rules

    def __str__(self):
        return (
            f"{super().__str__()}\n"
            f"Rolled-back rules: {self.rolled_back_rules }\n"
            f"Original exception: {self.orginal_exception}"
        )


def get_env_ips(vpc: str, application_environment: Environment) -> List[str]:
    account_name = f"{application_environment.session.profile_name}-vpc"
    vpc_name = vpc if vpc else account_name
    ssm_client = application_environment.session.client("ssm")

    try:
        param_value = ssm_client.get_parameter(Name=f"/{vpc_name}/EGRESS_IPS")["Parameter"]["Value"]
    except ssm_client.exceptions.ParameterNotFound:
        click.secho(f"No parameter found with name: /{vpc_name}/EGRESS_IPS")
        raise click.Abort

    return [ip.strip() for ip in param_value.split(",")]


class MaintenancePage:
    def __init__(
        self,
        application: Application,
        io: ClickIOProvider = ClickIOProvider(),
        load_balancer: LoadBalancerProvider = LoadBalancerProvider,
        get_env_ips: Callable[[str, Environment], List[str]] = get_env_ips,
    ):
        self.application = application
        self.io = io
        self.load_balancer_provider = load_balancer  # TODO instanciate
        self.load_balancer: LoadBalancerProvider = None
        self.get_env_ips = get_env_ips

    def _get_deployed_load_balanced_web_services(self, app: Application, svc: List[str]):
        if "*" in svc:
            services = [s for s in app.services.values() if s.kind == "Load Balanced Web Service"]
        else:
            all_services = [get_app_service(app, s) for s in list(svc)]
            services = [s for s in all_services if s.kind == "Load Balanced Web Service"]
        if not services:
            raise LoadBalancedWebServiceNotFoundException(app.name)
        return services

    # TODO: inject load balancer provider in activate method to avoid passing load balancer provider in init?
    def activate(self, env: str, services: List[str], template: str, vpc: Union[str, None]):

        services = self._get_deployed_load_balanced_web_services(self.application, services)
        application_environment = get_app_environment(self.application, env)
        self.load_balancer = self.load_balancer_provider(application_environment.session)

        try:
            https_listener = self.load_balancer.get_https_listener_for_application(
                application_environment.session, self.application.name, env
            )
            current_maintenance_page = self.__get_maintenance_page_type(https_listener)
            remove_current_maintenance_page = False
            if current_maintenance_page:
                remove_current_maintenance_page = self.io.confirm(
                    f"There is currently a '{current_maintenance_page}' maintenance page for the {env} "
                    f"environment in {self.application.name}.\nWould you like to replace it with a '{template}' "
                    f"maintenance page?"
                )
                if not remove_current_maintenance_page:
                    return

            if remove_current_maintenance_page or self.io.confirm(
                f"You are about to enable the '{template}' maintenance page for the {env} "
                f"environment in {self.application.name}.\nWould you like to continue?"
            ):
                if current_maintenance_page and remove_current_maintenance_page:
                    self.__remove_maintenance_page(https_listener)

                allowed_ips = self.get_env_ips(vpc, application_environment)

                self.add_maintenance_page(
                    https_listener,
                    self.application.name,
                    env,
                    services,
                    allowed_ips,
                    template,
                )
                self.io.info(
                    f"Maintenance page '{template}' added for environment {env} in application {self.application.name}",
                )

        except LoadBalancerNotFoundException:
            # TODO push exception to command layer
            self.io.abort_with_error(
                f"No load balancer found for environment {env} in the application {self.application.name}.",
            )

        except ListenerNotFoundException:
            # TODO push exception to command layer
            self.io.abort_with_error(
                f"No HTTPS listener found for environment {env} in the application {self.application.name}.",
            )

    def deactivate(self, env: str):
        application_environment = get_app_environment(self.application, env)

        self.load_balancer = self.load_balancer_provider(application_environment.session)

        try:
            https_listener = self.load_balancer.get_https_listener_for_application(
                application_environment.session, self.application.name, env
            )
            current_maintenance_page = self.__get_maintenance_page_type(https_listener)

            # TODO discuss, reduce number of return statements but more nested if statements
            if not current_maintenance_page:
                self.io.warn("There is no current maintenance page to remove")
                return

            if not self.io.confirm(
                f"There is currently a '{current_maintenance_page}' maintenance page, "
                f"would you like to remove it?"
            ):
                return

            self.__remove_maintenance_page(https_listener)
            self.io.info(
                f"Maintenance page removed from environment {env} in application {self.application.name}",
            )

        except LoadBalancerNotFoundException:
            # TODO push exception to command layer
            self.io.abort_with_error(
                f"No load balancer found for environment {env} in the application {self.application.name}.",
            )

        except ListenerNotFoundException:
            # TODO push exception to command layer
            self.io.abort_with_error(
                f"No HTTPS listener found for environment {env} in the application {self.application.name}.",
            )

    def add_maintenance_page(
        self,
        listener_arn: str,
        app: str,
        env: str,
        services: List[Service],
        allowed_ips: List[str],
        template: str = "default",
    ):

        maintenance_page_content = get_maintenance_page_template(template)
        bypass_value = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))

        rule_priority = itertools.count(start=1)
        maintenance_page_host_header_conditions = []
        try:
            for svc in services:
                target_group_arn = self.load_balancer.find_target_group(app, env, svc.name)

                # not all of an application's services are guaranteed to have been deployed to an environment
                if not target_group_arn:
                    continue

                service_conditions = self.load_balancer.get_host_header_conditions(
                    listener_arn, target_group_arn
                )

                for ip in allowed_ips:
                    self.load_balancer.create_header_rule(
                        listener_arn,
                        target_group_arn,
                        "X-Forwarded-For",
                        [ip],
                        "AllowedIps",
                        next(rule_priority),
                        service_conditions,
                    )
                    self.load_balancer.create_source_ip_rule(
                        listener_arn,
                        target_group_arn,
                        [ip],
                        "AllowedSourceIps",
                        next(rule_priority),
                        service_conditions,
                    )

                self.load_balancer.create_header_rule(
                    listener_arn,
                    target_group_arn,
                    "Bypass-Key",
                    [bypass_value],
                    "BypassIpFilter",
                    next(rule_priority),
                    service_conditions,
                )

                # add to accumilating list of conditions for maintenace page rule
                maintenance_page_host_header_conditions.extend(service_conditions)

            self.io.info(
                f"\nUse a browser plugin to add `Bypass-Key` header with value {bypass_value} to your requests. For more detail, visit https://platform.readme.trade.gov.uk/next-steps/put-a-service-under-maintenance/",
            )

            self.load_balancer.create_rule(
                listener_arn=listener_arn,
                priority=next(rule_priority),
                conditions=[
                    {
                        "Field": "path-pattern",
                        "PathPatternConfig": {"Values": ["/*"]},
                    },
                    {
                        "Field": "host-header",
                        "HostHeaderConfig": {
                            "Values": sorted(
                                list(
                                    {
                                        value
                                        for condition in maintenance_page_host_header_conditions
                                        for value in condition["HostHeaderConfig"]["Values"]
                                    }
                                )
                            )
                        },
                    },
                ],
                actions=[
                    {
                        "Type": "fixed-response",
                        "FixedResponseConfig": {
                            "StatusCode": "503",
                            "ContentType": "text/html",
                            "MessageBody": maintenance_page_content,
                        },
                    }
                ],
                tags=[
                    {"Key": "name", "Value": "MaintenancePage"},
                    {"Key": "type", "Value": template},
                ],
            )
        except Exception as e:
            deleted_rules = self.__clean_up_maintenance_page_rules(listener_arn)
            raise FailedToActivateMaintenancePageException(
                app, env, f"{e}:\n {traceback.format_exc()}", deleted_rules
            )

    def __clean_up_maintenance_page_rules(
        self, listener_arn: str, fail_when_not_deleted: bool = False
    ) -> dict[str, bool]:

        tag_descriptions = self.load_balancer.get_rules_tag_descriptions_by_listener_arn(
            listener_arn
        )

        deletes = {}
        for name in ["MaintenancePage", "AllowedIps", "BypassIpFilter", "AllowedSourceIps"]:
            deleted = self.load_balancer.delete_listener_rule_by_tags(tag_descriptions, name)
            deletes[name] = bool(deleted)
            if fail_when_not_deleted and name == "MaintenancePage" and not deleted:
                raise ListenerRuleNotFoundException()

        return deletes

    def __remove_maintenance_page(self, listener_arn: str) -> dict[str, bool]:
        self.__clean_up_maintenance_page_rules(listener_arn, True)

    def __get_maintenance_page_type(self, listener_arn: str) -> Union[str, None]:
        tag_descriptions = self.load_balancer.get_rules_tag_descriptions_by_listener_arn(
            listener_arn
        )
        maintenance_page_type = None
        for description in tag_descriptions:
            tags = {t["Key"]: t["Value"] for t in description["Tags"]}
            if tags.get("name") == "MaintenancePage":
                maintenance_page_type = tags.get("type")

        return maintenance_page_type


def get_app_service(application: Application, svc_name: str) -> Service:
    application_service = application.services.get(svc_name)

    if not application_service:
        # TODO raise exception instead of abort
        click.secho(
            f"The service {svc_name} was not found in the application {application.name}. "
            f"It either does not exist, or has not been deployed.",
            fg="red",
        )
        raise click.Abort

    return application_service


def get_app_environment(application: Application, env_name: str) -> Environment:
    application_environment = application.environments.get(env_name)

    if not application_environment:
        click.secho(
            f"The environment {env_name} was not found in the application {application.name}. "
            f"It either does not exist, or has not been deployed.",
            fg="red",
        )
        raise click.Abort

    return application_environment


def get_maintenance_page_template(template) -> str:
    template_contents = (
        Path(__file__)
        .parent.parent.joinpath(
            f"templates/svc/maintenance_pages/{template}.html",
        )
        .read_text()
        .replace("\n", "")
    )

    # [^\S]\s+ - Remove any space that is not preceded by a non-space character.
    return re.sub(r"[^\S]\s+", "", template_contents)
