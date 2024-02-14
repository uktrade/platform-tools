import click
from cloudfoundry_client.client import CloudFoundryClient


def get_cloud_foundry_client_or_abort():
    try:
        client = CloudFoundryClient.build_from_cf_config()
        click.secho("Logged in to Cloud Foundry", fg="green")
        return client
    except Exception as ex:
        click.secho("Could not connect to Cloud Foundry: ", fg="red", nl=False)
        click.secho(str(ex))
        click.secho("Please log in with: cf login", fg="yellow")
        exit(1)
