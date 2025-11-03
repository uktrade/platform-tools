import click

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

    # TODO pass in list of environments to create value for
    def create(self, app_name, name):
        self.application = (
            self.load_application_fn(app_name) if not self.application else self.application
        )

        get_secret_name = lambda x: f"/platform/{app_name}/{x}/secrets/{name.upper()}"

        # TODO either gets environments from list or use all environments loaded
        for _, environment in self.application.environments.items():

            click.echo(environment)

            value = click.prompt(
                f"  {environment.name}", hide_input=True, confirmation_prompt=False, type=str
            )

            # TODO check if parameter exists before trying to create
            # TODO what to do fail or overwrite? Is it an option
            # TODO throw error if values exists for some of the selected environments suggest using overwrite flag

            click.echo(
                f"Creating ssm value {value} in {get_secret_name(environment.name)} with tags application: {app_name} and environment: {environment.name}"
            )

        # TODO build dictionary of values to set for each env then batch create values after all input

        # ssm_client = environment.session.client("ssm")
        # ssm_client.put_parameter(
        #     Name=get_secret_name(environment.name),
        #     Value=value,
        #     Overwrite=False,
        #     Type='SecureString',
        #     Tags=[
        #         {
        #             'Key': 'application',
        #             'Value': app_name
        #         },{
        #             'Key': 'environment',
        #             'Value': environment.name
        #         },
        #     ]

        # )
