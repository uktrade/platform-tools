import click

from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.parameter_store import ParameterStore
from dbt_platform_helper.utils.application import load_application


class Secrets:

    def __init__(
        self,
        load_application=load_application,
        io: ClickIOProvider = ClickIOProvider(),
        parameter_store_provider: ParameterStore = ParameterStore,
    ):
        self.load_application_fn = load_application
        self.application = None
        self.io = io
        self.parameter_store_provider: ParameterStore = parameter_store_provider
        self.parameter_store: ParameterStore = None

    # def __get_parameter_store(self,):
    #     if not self.parameter_store:
    #         self.parameter_store = self.parameter_store_provider(self.session.client("ssm"))
    #     return self.parameter_store

    def create(self, app_name, name, overwrite):
        self.application = (
            self.load_application_fn(app_name) if not self.application else self.application
        )

        accounts = {}
        for _, environment in self.application.environments.items():
            if environment.account_id not in accounts:
                accounts[environment.account_id] = environment.session

        no_access = []
        for account, session in accounts.items():
            has_access = False
            sts = session.client("sts")
            iam = session.client("iam")

            sts_arn = sts.get_caller_identity()["Arn"]
            role_name = sts_arn.split("/")[1]

            managed_policies = iam.list_attached_role_policies(RoleName=role_name)[
                "AttachedPolicies"
            ]
            for policy in managed_policies:
                if policy["PolicyName"] == "AdministratorAccess":
                    has_access = True

            if has_access:
                continue  # if has access move onto next account

            role_policies = iam.list_role_polcies(RoleName=role_name)["PolicyNames"]

            for policy in role_policies:
                policy_doc = iam.get_role_policy(RoleName=role_name, PolicyName=policy)[
                    "PolicyDocument"
                ]
                for statement in policy_doc["Statement"]:
                    if "ssm:*" in statement["Action"] or "ssm:PutParmeter" in statement["Action"]:
                        has_access = True

            if not has_access:
                no_access.append(account)

        if no_access:
            account_ids = ", ".join(no_access)
            raise PlatformException(
                f"You do not have SSM write access to the following AWS accounts: {account_ids}"
            )

        get_secret_name = lambda x: f"/platform/{app_name}/{x}/secrets/{name.upper()}"

        # TODO if overwrite == false
        # Check if params exist
        # throw error if param exists

        values = {}
        for _, environment in self.application.environments.items():

            click.echo(environment)

            # TODO add into click provider
            value = click.prompt(
                f"  {environment.name}", hide_input=True, confirmation_prompt=False, type=str
            )

            values[environment.name] = value

        for environment_name, secret_value in values.items():
            environment = self.application.environments[environment_name]

            click.echo(
                f"Creating ssm value {secret_value} in {get_secret_name(environment.name)} with tags application: {app_name} and environment: {environment.name}"
            )

            # ssm_client = environment.session.client("ssm")
            # ssm_client.put_parameter(
            #     Name=get_secret_name(environment.name),
            #     Value=secret_value,
            #     Overwrite=overwrite,
            #     Type="SecureString",
            #     Tags=[
            #         {
            #             "Key": "application",
            #             "Value": app_name
            #         },
            #         {
            #             "Key": "environment",
            #             "Value": environment.name
            #         },
            #     ]
            # )
