import botocore

from dbt_platform_helper.constants import MANAGED_BY_PLATFORM
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

    def _check_ssm_write_access(self, accounts):
        """
        Check access.

        Cannot use iam.simulate_principal_policy due to read accounts not having
        access
        """
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

            inline_policies = iam.list_role_policies(RoleName=role_name)["PolicyNames"]

            for policy in inline_policies:
                policy_doc = iam.get_role_policy(RoleName=role_name, PolicyName=policy)[
                    "PolicyDocument"
                ]
                for statement in policy_doc["Statement"]:
                    if "ssm:*" in statement["Action"] or "ssm:PutParameter" in statement["Action"]:
                        has_access = True
                        break
                if has_access:
                    break

            if not has_access:
                no_access.append(account)

        if no_access:
            account_ids = "', '".join(no_access)
            raise PlatformException(
                f"You do not have AWS Parameter Store write access to the following AWS accounts: '{account_ids}'"
            )

    def _check_for_existing_params(self, get_secret_name):
        found_params = []
        for _, environment in self.application.environments.items():
            parameter_store: ParameterStore = self.parameter_store_provider(
                environment.session.client("ssm")
            )
            try:
                param = parameter_store.get_ssm_parameter_by_name(get_secret_name(environment.name))
                if param:
                    found_params.append(environment.name)
            except botocore.exceptions.ClientError as error:
                if error.response["Error"]["Code"] == "ParameterNotFound":
                    pass
                else:
                    raise PlatformException(error)

        return found_params

    def create(self, app_name, name, overwrite):
        self.application = (
            self.load_application_fn(app_name) if not self.application else self.application
        )

        accounts = {}
        for _, environment in self.application.environments.items():
            if environment.account_id not in accounts:
                accounts[environment.account_id] = environment.session

        self._check_ssm_write_access(accounts)

        get_secret_name = lambda x: f"/platform/{app_name}/{x}/secrets/{name.upper()}"
        found_params = self._check_for_existing_params(get_secret_name)

        if overwrite is False and found_params:
            envs = "', '".join(found_params)
            raise PlatformException(
                f"AWS Parameter Store secret '{name.upper()}' already exists for the following environments: '{envs}'. \nUse the --overwrite flag to replacing existing secret values."
            )

        values = {}
        for _, environment in self.application.environments.items():
            value = self.io.input(
                f"Please enter value for secret '{name.upper()}' in environment '{environment.name}'",
                hide_input=True,
            )
            values[environment.name] = value

        for environment_name, secret_value in values.items():

            environment = self.application.environments[environment_name]
            parameter_store: ParameterStore = self.parameter_store_provider(
                environment.session.client("ssm")
            )

            data_dict = dict(
                Name=get_secret_name(environment.name),
                Value=secret_value,
                Overwrite=False,
                Type="SecureString",
                Tags=[
                    {"Key": "application", "Value": app_name},
                    {"Key": "environment", "Value": environment.name},
                    {"Key": "managed-by", "Value": MANAGED_BY_PLATFORM},
                ],
            )

            # If in found params we are overwriting
            if overwrite and environment_name in found_params:
                data_dict["Overwrite"] = True
                del data_dict["Tags"]
            self.io.debug(
                f"Creating AWS Parameter Store secret {get_secret_name(environment.name)} ..."
            )
            parameter_store.put_parameter(data_dict)

        self.io.info(
            "\nTo check or update your secrets head over to the AWS Console https://eu-west-2.console.aws.amazon.com/systems-manager/parameters/\n"
            "You can attach secrets into ECS container by adding them to the `secrets` section of your 'service-config.yml' file."
        )

        self.io.info(
            message=f"```\nsecrets:\n\t{name.upper()}: /platform/${{PLATFORM_APPLICATION_NAME}}/${{PLATFORM_ENVIRONMENT_NAME}}/secrets/{name.upper()}\n```",
            fg="cyan",
        )
