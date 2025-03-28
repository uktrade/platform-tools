from slack_sdk import WebClient
from slack_sdk.models import blocks

from dbt_platform_helper.utils.arn_parser import ARN


class SlackChannelNotifier:
    def __init__(self, slack_token: str, slack_channel_id: str):
        self.client = WebClient(slack_token)
        self.slack_channel_id = slack_channel_id

    def post_update(self, slack_ref, message_blocks, message):
        args = {
            "channel": self.slack_channel_id,
            "blocks": message_blocks,
            "text": message,
            "unfurl_links": False,
            "unfurl_media": False,
        }
        self.client.chat_update(ts=slack_ref, **args)

    def post_new(self, message_blocks, message, reply_broadcast=None, thread_ts=None):
        args = {
            "channel": self.slack_channel_id,
            "blocks": message_blocks,
            "text": message,
            "reply_broadcast": reply_broadcast,
            "unfurl_links": False,
            "unfurl_media": False,
            "thread_ts": thread_ts,
        }
        self.client.chat_postMessage(ts=None, **args)


# TODO untangle responsibilities
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
        message_blocks = self._get_message_blocks(build_arn, commit_sha, message, repository)

        if slack_ref:
            return self.notifier.post_update(slack_ref, message_blocks, message)
        else:
            return self.notifier.post_new(message_blocks, message)

    def _get_message_blocks(self, build_arn: str, commit_sha: str, message: str, repository: str):
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
                        blocks.TextObject(type="mrkdwn", text=element)
                        for element in context_elements
                    ]
                )
            )
        return message_blocks

    def add_comment(
        self,
        slack_ref: str,
        message: str,
        title: str,
        send_to_main_channel: bool,
    ):
        message_blocks = [blocks.SectionBlock(text=blocks.TextObject(type="mrkdwn", text=message))]
        self.notifier.post_new(
            message_blocks=message_blocks,
            message=title if title else message,
            reply_broadcast=send_to_main_channel,
            thread_ts=slack_ref,
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
