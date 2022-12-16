#!/usr/bin/env python

import requests

import boto3
import click
from cloudfoundry_client.client import CloudFoundryClient
import requests


client = boto3.client('ssm')

# TODO: optional SSM or secret manager

SSM_BASE_PATH = "/copilot/{app}/{env}/secrets/"
SSM_PATH = "/copilot/{app}/{env}/secrets/{name}"
SSM_OUTPUT = " {name}: /copilot/${{COPILOT_APPLICATION_NAME}}/${{COPILOT_ENVIRONMENT_NAME}}/secrets/{name}"


# Do not copy these env vars form gov paas
SKIP_ENV_VARS = ["GIT_COMMIT", "GIT_BRANCH"]


@click.command()
@click.option('--paas', prompt="Enter path of the paas app in the format {org}/{space}/{app}", help='The {org}/{space}/{app} of the paas app')
@click.option('--app', prompt="Enter copilot app name", help='The name of the copilot app')
@click.option('--env', prompt='Enter copilot env name', help='The person to greet.')
@click.option('--overwrite', is_flag=True, show_default=True, default=False, help='Overwrite existing secrets?')
@click.option('--dry-run', is_flag=True, show_default=True, default=False, help='dry run')
def cli(paas, app, env, overwrite, dry_run):
    env_vars = get_paas_env_vars(paas)
    ssm_secret_names = get_ssm_secret_names(app, env)

    if overwrite:
        click.echo("NOTE: tags are not changed in overwritten secrets")

    for name, value in env_vars.items():
        if name not in SKIP_ENV_VARS:
            ssm_path = SSM_PATH.format(app=app, env=env, name=name)

            # SSM won't allow us to create empty parameters so set empty fields
            # to a non null value
            param_value = "empty" if value == "" else value
            param_exists = name in ssm_secret_names

            if not dry_run and (overwrite or not param_exists):
                set_ssm_param(app, env, ssm_path, param_value, overwrite, param_exists)

            text = "Created" if name not in ssm_secret_names else "Overwritten" if overwrite else "NOT overwritten"

            click.echo(f"{text} {ssm_path}")

    if not dry_run:
        print_yaml(app, env)


def get_paas_env_vars(paas):
    client = CloudFoundryClient.build_from_cf_config()

    org, space, app = paas.split("/")

    env_vars = None

    for paas_org in client.v2.organizations:
        if paas_org["entity"]["name"] == org:
            for paas_space in paas_org.spaces():
                if paas_space["entity"]["name"] == space:
                    for paas_app in paas_space.apps():
                        if paas_app["entity"]["name"] == app:
                            env_vars = paas_app["entity"]["environment_json"]

    if not env_vars:
        raise Exception(f"Application {paas} not found")

    return dict(env_vars)


def set_ssm_param(app, env, param_name, param_value, overwrite, exists):
    args = dict(
        Name=param_name,
        Description='copied from cloudfoundry',
        Value=param_value,
        Type='SecureString',
        Overwrite=overwrite,
        Tags=[
                {
                    'Key': 'copilot-application',
                    'Value': app
                },
                {
                    'Key': 'copilot-environment',
                    'Value': env
                },
        ],
    )

    if overwrite and exists:
        # Tags can't be updated when overwriting
        del args["Tags"]

    response = client.put_parameter(**args)


def get_ssm_secret_names(app, env):
    client = boto3.client('ssm')

    path = SSM_BASE_PATH.format(app=app, env=env)

    params = dict(
        Path=path,
        Recursive=False,
        WithDecryption=True,
        MaxResults=10,
    )

    secret_names = []

    while True:
        response = client.get_parameters_by_path(
            **params
        )

        for secret in response["Parameters"]:
            secret_names.append(secret["Name"].split("/")[-1])

        if "NextToken" in response:
            params["NextToken"] = response["NextToken"]
        else:
            break

    return sorted(secret_names)


def print_yaml(app, env):

    secret_names = get_ssm_secret_names(app, env)

    print("Add the following to your service's manifest.yml")

    for secret in secret_names:
        click.echo(SSM_OUTPUT.format(name=secret))

    click.echo("Total secrets: {}".format(len(secret_names)))


if __name__ == '__main__':
    cli()
