import click
from slack_sdk import WebClient
from slack_sdk.models import blocks

from dbt_platform_helper.utils.arn_parser import ARN
from dbt_platform_helper.utils.click import ClickDocOptGroup
from dbt_platform_helper.utils.versioning import (
    check_platform_helper_version_needs_update,
)


@click.group(cls=ClickDocOptGroup, help="Send Slack notifications")
def notify():
    check_platform_helper_version_needs_update()


@notify.command(help="Send environment progress notifications")
@click.argument("slack-channel-id")
@click.argument("slack-token")
@click.argument("message")
@click.option("--build-arn")
@click.option("--repository")
@click.option("--commit-sha")
@click.option("--slack-ref", help="Slack message reference")
def environment_progress(
    slack_channel_id: str,
    slack_token: str,
    message: str,
    build_arn: str,
    repository: str,
    commit_sha: str,
    slack_ref: str,
):
    args = _get_slack_args(build_arn, commit_sha, message, repository, slack_channel_id)
    slack = _get_slack_client(slack_token)

    if slack_ref:
        response = slack.chat_update(ts=slack_ref, **args)
    else:
        response = slack.chat_postMessage(ts=slack_ref, **args)

    print(response["ts"])


def _get_slack_args(
    build_arn: str, commit_sha: str, message: str, repository: str, slack_channel_id: str
):
    context_elements = []
    if repository:
        context_elements.append(f"*Repository*: <https://github.com/{repository}|{repository}>")
        if commit_sha:
            context_elements.append(
                f"*Revision*: <https://github.com/{repository}/commit/{commit_sha}|{commit_sha}>"
            )
    if build_arn:
        context_elements.append(f"<{get_build_url(build_arn)}|Build Logs>")
    message_blocks = [
        blocks.SectionBlock(
            text=blocks.TextObject(type="mrkdwn", text=message),
        ),
    ]

    if context_elements:
        message_blocks.append(
            blocks.ContextBlock(
                elements=[
                    blocks.TextObject(type="mrkdwn", text=element) for element in context_elements
                ]
            )
        )

    args = {
        "channel": slack_channel_id,
        "blocks": message_blocks,
        "text": message,
        "unfurl_links": False,
        "unfurl_media": False,
    }
    return args


def _get_slack_client(token: str):
    return WebClient(token=token)


@notify.command(help="Add comment to a notification")
@click.argument("slack-channel-id")
@click.argument("slack-token")
@click.argument("slack-ref")
@click.argument("message")
@click.option("--title", default=None, help="Message title")
@click.option("--send-to-main-channel", default=False, help="Send to main channel")
def add_comment(
    slack_channel_id: str,
    slack_token: str,
    slack_ref: str,
    message: str,
    title: str,
    send_to_main_channel: bool,
):
    slack = _get_slack_client(slack_token)

    slack.chat_postMessage(
        channel=slack_channel_id,
        blocks=[blocks.SectionBlock(text=blocks.TextObject(type="mrkdwn", text=message))],
        text=title if title else message,
        reply_broadcast=send_to_main_channel,
        unfurl_links=False,
        unfurl_media=False,
        thread_ts=slack_ref,
    )


def get_build_url(build_arn: str):
    try:
        arn = ARN(build_arn)
        url = (
            "https://{region}.console.aws.amazon.com/codesuite/codebuild/{account}/projects/{"
            "project}/build/{project}%3A{build_id}"
        )
        return url.format(
            region=arn.region,
            account=arn.account_id,
            project=arn.project.replace("build/", ""),
            build_id=arn.build_id,
        )
    except ValueError:
        return ""
