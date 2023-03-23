#!/usr/bin/env python

import boto3
import click
import json


def check_success(task, response):
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        print(f"{task} was a success...")
    else:
        print(f"{task} failed...")


def display_aws_account():
    client = boto3.client('iam', region_name='eu-west-2')

    # Check if account exists, if not create
    response = client.list_account_aliases()
    # Each AWS account should have an alias defined.

    if not response['AccountAliases']:
        account_name = input("No Account name has been defined\nPlease enter the name you wish to give to this account: ")
        if not click.confirm(f"You are about to update AWS Account name to: {account_name}\nDo you want to continue?"):
            exit()
        response  = client.create_account_alias(
            AccountAlias=account_name,
        )
        check_success("Create Account Alias", response)
    else:
        account_name=response['AccountAliases'][0]


    if not click.confirm(f"You are about to update AWS Account: {account_name}\nDo you want to continue?"):
        exit()

    return account_name


def import_pat(pat):
    client = boto3.client('codebuild', region_name='eu-west-2')

    response = client.import_source_credentials(
        token=pat,
        serverType='GITHUB',
        authType='PERSONAL_ACCESS_TOKEN',
        shouldOverwrite=True
    )

    check_success("GITHUB PAT import", response)


def check_github_conn(client):
    response = client.list_source_credentials()

    # If there are no source code creds defined then AWS is not linked to Github
    if not response['sourceCredentialsInfos']:
        if not click.confirm(f"Github not Linked in this AWS account\nDo you want to link with a PAT?"):
            exit()

        pat = input(
        '''
        Create a bots PAT with the following scope:
            repo:   status: Grants read/write access to public and private repository commit statuses.
            admin:  repo_hook: Grants full control of repository hooks.

        Enter in the PAT here:
        '''
        )

        import_pat(pat)


def check_service_role():
    client = boto3.client('iam', region_name='eu-west-2')

    try:
        response = client.get_role(
            RoleName='ci-CodeBuild-role'
        )

        role_arn = response['Role']['Arn']

    except client.exceptions.NoSuchEntityException:
        print ("Role for service does not exist run ./code-deploy-bootstrap.py create-codeploy-role")
        role_arn = ""
        exit()

    return (role_arn)


@click.group()
def cli():
    pass


@cli.command()
@click.option('--pat', help='PAT Token')
def link_github(pat):
    """
    Links CodeDeploy to Github via users PAT
    """
    account_name = display_aws_account()
    import_pat(pat)


@cli.command()
def create_codedeploy_role():
    """
    Add AWS Role needed for codedeploy
    """

    account_name = display_aws_account()

    with open('templates/put-codebuild-role-policy.json') as f:
        policy_doc = json.load(f)
    client = boto3.client('iam', region_name='eu-west-2')

    # A policy must be defined if not present.
    try:
        response = client.create_policy(
            PolicyName='ci-CodeBuild-policy',
            PolicyDocument=json.dumps(policy_doc),
            Description='Custom Policy for codebuild',
            Tags=[
                {
                    'Key': 'Name',
                    'Value': 'CustomPolicy'
                },
            ]
        )
        check_success("Create Policy", response)
    except client.exceptions.EntityAlreadyExistsException:
        print("Policy exists")

    with open('templates/create-codebuild-role.json') as f:
        role_doc = json.load(f)

    # Now create a role if not present and attache policy
    try:
        response = client.create_role(
            RoleName = 'ci-CodeBuild-role',
            AssumeRolePolicyDocument = json.dumps(role_doc)
        )
        check_success("Create Role", response)
    except client.exceptions.EntityAlreadyExistsException:
        print("Role exists")

    account_id = boto3.client('sts').get_caller_identity().get('Account')
    client.attach_role_policy(
        PolicyArn=f'arn:aws:iam::{account_id}:policy/ci-CodeBuild-policy',
        RoleName='ci-CodeBuild-role'
    )


@cli.command()
@click.option('--update', is_flag=True, show_default=True, default=False, help='Update config')
@click.option('--name', help='Name of project')
@click.option('--desc', help='Description of project')
@click.option('--git', help='Git url of code')
@click.option('--branch', help='Git branch')
@click.option('--buildspec', help='Location of buildspec file in repo')
@click.option('--builderimage', default="public.ecr.aws/h0i0h2o7/uktrade/ci-image-builder", help='Builder image')
def codedeploy(update, name, desc, git, branch, buildspec, builderimage):
    """
    Builds Code build boilerplate
    """

    account_name = display_aws_account()
    role_arn = check_service_role()
    client = boto3.client('codebuild', region_name='eu-west-2')
    check_github_conn(client)

    environment = {
            'type': 'LINUX_CONTAINER',
            'image': f'{builderimage}',
            'computeType': 'BUILD_GENERAL1_SMALL',
            'environmentVariables': [],
            'privilegedMode': True,
            'imagePullCredentialsType': 'SERVICE_ROLE'
    }

    source = {
        'type': 'GITHUB',
        'location': f'{git}',
        'buildspec': f'{buildspec}',
        'auth': {
            'type': 'OAUTH',
            'resource': 'AWS::CodeBuild::SourceCredential'
        },
    }

    artifacts = {
        'type': 'NO_ARTIFACTS'
    }

    logsConfig={
        'cloudWatchLogs': {
            'status': 'ENABLED',
        },
    }

    # Either update project or create a new project
    if update:
        response = client.update_project(
            name=name,
            description=desc,
            source=source,
            sourceVersion=branch,
            artifacts=artifacts,
            environment=environment,
            serviceRole=role_arn,
            logsConfig=logsConfig,
        )

        response_webhook = client.update_webhook(
            projectName=name,
            filterGroups=[
                [
                    {
                        'type': 'EVENT',
                        'pattern': 'PUSH',
                    },
                ],
            ],
            buildType='BUILD'
        )
        print("Project Updated")
    else:
        try:
            response = client.create_project(
                name=name,
                description=desc,
                source=source,
                sourceVersion=branch,
                artifacts=artifacts,
                environment=environment,
                serviceRole=role_arn,
                logsConfig=logsConfig,
            )

            response_webhook = client.create_webhook(
                projectName=name,
                filterGroups=[
                    [
                        {
                            'type': 'EVENT',
                            'pattern': 'PUSH',
                        },
                    ],
                ],
                buildType='BUILD'
            )

        except client.exceptions.ResourceAlreadyExistsException:
            print("Project already exist use:  ./code-deploy-bootstrap.py codedeploy --update")
            exit()

    check_success("Create Project", response)
    check_success("Create Webhook", response_webhook)


def update_paramter(name, description, value):
    client = boto3.client('ssm', region_name='eu-west-2')

    response = client.put_parameter(
        Name=name,
        Description=description,
        Value=value,
        Type='SecureString',
        Overwrite=True,
        Tier='Standard',
        DataType='text'
    )


@cli.command()
@click.option('--workspace', help='Slack Workspace id')
@click.option('--channel', help='Slack channel id')
@click.option('--token', help='Slack api token')
def slackcreds(workspace, channel, token):
    """
    Add Slack credentials into AWS Parameter Store
    """

    SLACK = {
        "workspace": {"name": "/codebuild/slack_workspace_id", "description": "Slack Workspace ID", "value": workspace},
        "channel": {"name": "/codebuild/slack_channel_id", "description": "Slack Channel ID", "value": channel},
        "token": {"name": "/codebuild/slack_api_token", "description": "Slack API Token", "value": token}
        }
    #breakpoint()
    print("Updating Parameter Store with SLACK Creds")
    account_name = display_aws_account()

    for item, value in SLACK.items():

        update_paramter(value['name'], value['description'], value['value'])

    print(f"AWS Account: {account_name} updated.")


if __name__ == "__main__":
    cli()
