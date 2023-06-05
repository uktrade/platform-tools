#!/usr/bin/env python
import json
import os
import click

from utils.aws import check_response, check_aws_conn

AWS_REGION = "eu-west-2"
DEFAULT_CI_BUILDER = "public.ecr.aws/uktrade/ci-image-builder"


def import_pat(pat, client):
    response = client.import_source_credentials(
        token=pat, serverType="GITHUB", authType="PERSONAL_ACCESS_TOKEN", shouldOverwrite=True
    )
    check_response(response)
    print("PAT successfully added")


def check_github_conn(client):
    response = client.list_source_credentials()

    # If there are no source code creds defined then AWS is not linked to Github
    if not response["sourceCredentialsInfos"]:
        if not click.confirm("Github not Linked in this AWS account\nDo you want to link with a PAT?"):
            exit()

        pat = input(
            """
            Create a bots PAT with the following scope:
                repo:   status: Grants read/write access to public and private repository commit statuses.
                admin:  repo_hook: Grants full control of repository hooks.

            Enter in the PAT here:
            """
        )

        import_pat(pat, client)


def check_service_role(project_profile):
    client = project_profile.client("iam", region_name=AWS_REGION)

    try:
        response = client.get_role(RoleName="ci-CodeBuild-role")
        role_arn = response["Role"]["Arn"]

    except client.exceptions.NoSuchEntityException:
        print("Role for service does not exist run ./codebuild_cli.py create-codeploy-role")
        role_arn = ""
        exit()

    return role_arn


def update_parameter(project_session, name, description, value):
    client = project_session.client("ssm", region_name=AWS_REGION)

    response = client.put_parameter(
        Name=name,
        Description=description,
        Value=value,
        Type="SecureString",
        Overwrite=True,
        Tier="Standard",
        DataType="text",
    )
    check_response(response)


def check_git_url(git):
    # Ensure the git format is https://github.com/<org>/<repository-name>
    git_part = git.split(":")

    print(git_part)
    if git_part[0] == "https":
        git_url = git
    elif git_part[0] == "git@github.com":
        git_url = "https://github.com/" + git_part[1]
    else:
        print(
            """
            Unable to recognise git url format, make sure its either:
            https://github.com/<org>/<repository-name>
            git@github.com:<org>/<repository-name>
            """
        )
        exit()
    return git_url


@click.group()
def codebuild():
    pass


@codebuild.command()
@click.option("--pat", help="PAT Token", required=True)
@click.option("--project-profile", help="aws account profile name", required=True)
def link_github(pat: str, project_profile: str) -> None:
    """
    Links CodeDeploy to Github via users PAT
    """

    project_session = check_aws_conn(project_profile)
    client = project_session.client("codebuild", region_name=AWS_REGION)
    import_pat(pat, client)


@codebuild.command()
@click.option("--project-profile", help="aws account profile name", required=True)
def create_codedeploy_role(project_profile):
    """
    Add AWS Role needed for codedeploy
    """

    project_session = check_aws_conn(project_profile)
    account_id = project_session.client("sts").get_caller_identity().get("Account")

    current_filepath = os.path.dirname(os.path.realpath(__file__))

    with open(f"{current_filepath}/templates/put-codebuild-role-policy.json") as f:
        policy_doc = json.load(f)
    client = project_session.client("iam", region_name=AWS_REGION)

    # A policy must be defined if not present.
    try:
        response = client.create_policy(
            PolicyName="ci-CodeBuild-policy",
            PolicyDocument=json.dumps(policy_doc),
            Description="Custom Policy for codebuild",
            Tags=[
                {"Key": "Name", "Value": "CustomPolicy"},
            ],
        )
        check_response(response)
        print("Policy created")

    except client.exceptions.EntityAlreadyExistsException:
        if not click.confirm("Policy exists.\nDo you want to update it?"):
            exit()
        try:
            response = client.create_policy_version(
                PolicyArn=f"arn:aws:iam::{account_id}:policy/ci-CodeBuild-policy",
                PolicyDocument=json.dumps(policy_doc),
                SetAsDefault=True,
            )
            check_response(response)
            print("Policy updated")

        except client.exceptions.LimitExceededException:
            print("You have hit the limit of max managed policies, please delete an existing version and try again")
            exit()

    with open(f"{current_filepath}/templates/create-codebuild-role.json") as f:
        role_doc = json.load(f)

    # Now create a role if not present and attache policy
    try:
        response = client.create_role(RoleName="ci-CodeBuild-role", AssumeRolePolicyDocument=json.dumps(role_doc))
        check_response(response)
        print("Role created")
    except client.exceptions.EntityAlreadyExistsException:
        print("Role exists")

    response = client.attach_role_policy(
        PolicyArn=f"arn:aws:iam::{account_id}:policy/ci-CodeBuild-policy", RoleName="ci-CodeBuild-role"
    )
    check_response(response)
    print("Policy attached to Role")


@codebuild.command()
@click.option("--update", is_flag=True, show_default=True, default=False, help="Update config")
@click.option("--name", required=True, help="Name of project")
@click.option("--desc", default="", help="Description of project")
@click.option("--git", required=True, help="Git url of code")
@click.option("--branch", required=True, help="Git branch")
@click.option("--buildspec", required=True, help="Location of buildspec file in repo")
@click.option("--builderimage", default=DEFAULT_CI_BUILDER, help="Builder image")
@click.option("--project-profile", required=True, help="aws account profile name")
@click.option("--release", is_flag=True, show_default=True, default=False, help="Trigger builds on release tags")
def codedeploy(update, name, desc, git, branch, buildspec, builderimage, project_profile, release):
    """
    Builds Code build boilerplate
    """

    git_url = check_git_url(git)
    project_session = check_aws_conn(project_profile)
    role_arn = check_service_role(project_session)
    client = project_session.client("codebuild", region_name=AWS_REGION)
    check_github_conn(client)

    environment = {
        "type": "LINUX_CONTAINER",
        "image": f"{builderimage}",
        "computeType": "BUILD_GENERAL1_SMALL",
        "environmentVariables": [],
        "privilegedMode": True,
        "imagePullCredentialsType": "SERVICE_ROLE",
    }

    source = {
        "type": "GITHUB",
        "location": f"{git_url}",
        "buildspec": f"{buildspec}",
        "auth": {"type": "OAUTH", "resource": "AWS::CodeBuild::SourceCredential"},
    }

    artifacts = {"type": "NO_ARTIFACTS"}

    logsConfig = {
        "cloudWatchLogs": {
            "status": "ENABLED",
        },
    }

    if release:
        pattern = "^refs/tags/.*"
    else:
        pattern = f"^refs/heads/{branch}"

    # Either update project or create a new project
    if update:
        try:
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
        except client.exceptions.ResourceNotFoundException:
            print("Unable to update a project that does not exist, drop the --update flag")
            exit()

        response_webhook = client.update_webhook(
            projectName=name,
            filterGroups=[
                [
                    {
                        "type": "EVENT",
                        "pattern": "PUSH",
                    },
                    {"type": "HEAD_REF", "pattern": pattern},
                ],
            ],
            buildType="BUILD",
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
                            "type": "EVENT",
                            "pattern": "PUSH",
                        },
                        {"type": "HEAD_REF", "pattern": pattern},
                    ],
                ],
                buildType="BUILD",
            )

        except client.exceptions.ResourceAlreadyExistsException:
            print("Project already exists, use the --update flag")
            exit()

    check_response(response)
    check_response(response_webhook)
    print(f"Codebuild project {name} created")


@codebuild.command()
@click.option("--workspace", help="Slack Workspace id", required=True)
@click.option("--channel", help="Slack channel id", required=True)
@click.option("--token", help="Slack api token", required=True)
@click.option("--project-profile", help="aws account profile name", required=True)
def slackcreds(workspace, channel, token, project_profile):
    """
    Add Slack credentials into AWS Parameter Store
    """
    project_session = check_aws_conn(project_profile)

    SLACK = {
        "workspace": {
            "name": "/codebuild/slack_workspace_id",
            "description": "Slack Workspace ID",
            "value": workspace,
        },
        "channel": {"name": "/codebuild/slack_channel_id", "description": "Slack Channel ID", "value": channel},
        "token": {"name": "/codebuild/slack_api_token", "description": "Slack API Token", "value": token},
    }

    if not click.confirm("Updating Parameter Store with Slack credentials.\nDo you want to update it?"):
        exit()

    for item, value in SLACK.items():
        update_parameter(project_session, value["name"], value["description"], value["value"])
    print("Paramater Store updated")


if __name__ == "__main__":
    codebuild()
