from slack_sdk import WebClient
from slack_sdk.models import blocks

from dbt_platform_helper.utils.arn_parser import ARN


class SlackChannelNotifier:
    def __init__(self, slack_token: str, slack_channel_id: str):
        self.client = WebClient(slack_token)
        self.slack_channel_id = slack_channel_id

    def post_update(self, message_ref, message, context=None):
        args = {
            "channel": self.slack_channel_id,
            "blocks": self._build_message_blocks(message, context),
            "text": message,
            "unfurl_links": False,
            "unfurl_media": False,
        }
        self.client.chat_update(ts=message_ref, **args)

    def post_new(self, message, context=None, title=None, reply_broadcast=None, thread_ref=None):
        args = {
            "channel": self.slack_channel_id,
            "blocks": self._build_message_blocks(message, context),
            "text": title if title else message,
            "reply_broadcast": reply_broadcast,
            "unfurl_links": False,
            "unfurl_media": False,
            "thread_ts": thread_ref,
        }
        self.client.chat_postMessage(ts=None, **args)

    def _build_message_blocks(self, message, context):
        message_blocks = [
            blocks.SectionBlock(
                text=blocks.TextObject(type="mrkdwn", text=message),
            ),
        ]

        if context:
            message_blocks.append(
                blocks.ContextBlock(
                    elements=[blocks.TextObject(type="mrkdwn", text=element) for element in context]
                )
            )
        return message_blocks


class Notify:
    def __init__(self, notifier: SlackChannelNotifier):
        self.notifier = notifier

    def environment_progress(
        self,
        message: str,
        build_arn: str = None,
        repository: str = None,
        commit_sha: str = None,
        slack_ref: str = None,
    ):
        context = []

        if repository:
            context.append(f"*Repository*: <https://github.com/{repository}|{repository}>")
            if commit_sha:
                context.append(
                    f"*Revision*: <https://github.com/{repository}/commit/{commit_sha}|{commit_sha}>"
                )

        if build_arn:
            context.append(f"<{get_build_url(build_arn)}|Build Logs>")

        if slack_ref:
            return self.notifier.post_update(slack_ref, message, context)
        else:
            return self.notifier.post_new(message, context)

    def add_comment(
        self,
        slack_ref: str,
        message: str,
        title: str,
        send_to_main_channel: bool,
    ):
        self.notifier.post_new(
            message=message,
            title=title,
            context=[],
            reply_broadcast=send_to_main_channel,
            thread_ref=slack_ref,
        )


# This utility probably belongs somewhere else
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
