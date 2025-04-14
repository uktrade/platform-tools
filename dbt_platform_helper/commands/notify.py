import click

from dbt_platform_helper.domain.notify import Notify
from dbt_platform_helper.domain.versioning import PlatformHelperVersioning
from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.slack_channel_notifier import SlackChannelNotifier
from dbt_platform_helper.utils.click import ClickDocOptGroup


@click.group(cls=ClickDocOptGroup, help="Send Slack notifications")
def notify():
    PlatformHelperVersioning().check_if_needs_update()


@notify.command(
    help="Send environment progress notifications. This creates (or updates if --slack-ref is provided) the top level message to the channel.",
    deprecated=True,
)
@click.argument("slack-channel-id")
@click.argument("slack-token")
@click.argument("message")
@click.option("--build-arn")
@click.option("--repository")
@click.option("--commit-sha")
@click.option("--slack-ref", help="Slack message reference of the message to update")
@click.pass_context
def environment_progress(
    ctx,
    slack_channel_id: str,
    slack_token: str,
    message: str,
    build_arn: str,
    repository: str,
    commit_sha: str,
    slack_ref: str,
):

    ctx.invoke(
        post_message,
        slack_channel_id=slack_channel_id,
        slack_token=slack_token,
        message=message,
        build_arn=build_arn,
        repository=repository,
        commit_sha=commit_sha,
        slack_ref=slack_ref,
    )


@notify.command(
    help="Send Slack notifications. This creates (or updates if --slack-ref is provided) the top level message to the channel."
)
@click.argument("slack-channel-id")
@click.argument("slack-token")
@click.argument("message")
@click.option("--build-arn")
@click.option("--repository")
@click.option("--commit-sha")
@click.option("--slack-ref", help="Slack message reference of the message to update")
def post_message(
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
        slack_notifier = SlackChannelNotifier(slack_token, slack_channel_id)
        result = Notify(slack_notifier).post_message(
            original_message_ref=slack_ref,
            message=message,
            build_arn=build_arn,
            repository=repository,
            commit_sha=commit_sha,
        )

        io.info(result)
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
        slack_notifier = SlackChannelNotifier(slack_token, slack_channel_id)
        Notify(slack_notifier).add_comment(
            message=message,
            title=title,
            reply_broadcast=send_to_main_channel,
            original_message_ref=slack_ref,
        )
    except PlatformException as err:
        ClickIOProvider().abort_with_error(str(err))
