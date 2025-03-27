import click
from slack_sdk.models import blocks

from dbt_platform_helper.domain.notify import Notify
from dbt_platform_helper.domain.notify import SlackClient
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.group(cls=ClickDocOptGroup, help="Send Slack notifications")
def notify():
    PlatformHelperVersioning().check_if_needs_update()


@notify.command(
    help="Send environment progress notifications. This creates (or updates if --slack-ref is provided) the top level message to the channel."
)
@click.argument("slack-channel-id")
@click.argument("slack-token")
@click.argument("message")
@click.option("--build-arn")
@click.option("--repository")
@click.option("--commit-sha")
@click.option("--slack-ref", help="Slack message reference of the message to update")
def environment_progress(
    slack_channel_id: str,
    slack_token: str,
    message: str,
    build_arn: str,
    repository: str,
    commit_sha: str,
    slack_ref: str,
):
    try:
        io = ClickIOProvider()
        client = SlackClient(slack_token, slack_channel_id)
        response = Notify(client).environment_progress(
            slack_ref,
            message,
            build_arn,
            repository,
            commit_sha,
        )

        io.info(response["ts"])
    except PlatformException as err:
        io.abort_with_error(str(err))


@notify.command(help="Add a comment to an existing Slack message")
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
    try:
        client = SlackClient(slack_token, slack_channel_id)
        Notify(client).add_comment(
            blocks=[blocks.SectionBlock(text=blocks.TextObject(type="mrkdwn", text=message))],
            text=title if title else message,
            reply_broadcast=send_to_main_channel,
            unfurl_links=False,
            unfurl_media=False,
            thread_ts=slack_ref,
        )
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))
