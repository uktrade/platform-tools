import click
import boto3
import botocore


def check_aws_conn(aws_profile: str) -> boto3.session.Session:
    # Check that the aws profile exists and is set.
    click.secho("Checking AWS connection...", fg='cyan')

    try:
        session = boto3.session.Session(profile_name=aws_profile)
    except botocore.exceptions.ProfileNotFound:
        click.secho("AWS profile not configured, please ensure they are set.", fg='red')
        exit()
    except botocore.errorfactory.UnauthorizedException:
        click.secho(
            "The SSO session associated with this profile has expired or is otherwise invalid.  " \
            "To refresh this SSO session run aws sso login with the corresponding profile",
        fg='red')
        exit()

    sts = session.client("sts")
    try:
        sts.get_caller_identity()
        click.secho("Credentials are valid.", fg='green')
    except botocore.exceptions.SSOTokenLoadError:
        click.secho(f"Credentials are NOT valid.  \nPlease login with: aws sso login --profile {aws_profile}", fg='red')
        exit()
    except botocore.exceptions.UnauthorizedSSOTokenError:
        click.secho(
            "The SSO session associated with this profile has expired or is otherwise invalid.  " \
            "To refresh this SSO session run aws sso login with the corresponding profile",
        fg='red')
        exit()

    alias_client = session.client("iam")
    account_name = alias_client.list_account_aliases()["AccountAliases"]
    click.echo(click.style(f"Logged in with AWS account: ",fg='yellow') + 
               click.style(f"{account_name[0]}/{sts.get_caller_identity()['Account']}", fg='white', bold=True))
    click.echo(click.style(f"User: ",fg='yellow' ) + 
               click.style(f"{(sts.get_caller_identity()['UserId']).split(':')[-1]}", fg='white', bold=True))
    
    return session


def check_response(response):
    if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
        click.secho(f"Unknown response error from AWS.\nStatus Code: {response['ResponseMetadata']['HTTPStatusCode']}", 
                    fg='red')
        exit()
