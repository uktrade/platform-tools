from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.models import blocks

from dbt_platform_helper.platform_exception import PlatformException


class SlackChannelNotifierException(PlatformException):
    pass


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

        try:
            response = self.client.chat_update(ts=message_ref, **args)
            return response["ts"]
        except SlackApiError as e:
            raise SlackChannelNotifierException(f"Slack notification unsuccessful: {e}")

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

        try:
            response = self.client.chat_postMessage(ts=None, **args)
            return response["ts"]
        except SlackApiError as e:
            raise SlackChannelNotifierException(f"Slack notification unsuccessful: {e}")

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
