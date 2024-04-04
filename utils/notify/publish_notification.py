import os

from slack_sdk import WebClient
from slack_sdk.models import blocks

RELEASE_NOTES_URL = "https://github.com/uktrade/platform-tools/releases/latest"


class PublishNotify:

    def __init__(self, send_notifications: bool = True):
        self.send_notifications = send_notifications

        if self.send_notifications:
            try:
                self.slack = WebClient(token=os.environ["SLACK_TOKEN"])
                self.channel = os.environ["SLACK_CHANNEL_ID"]
            except KeyError as e:
                raise ValueError(f"{e} environment variable must be set")

    def post_publish_update(self, version: str):
        if not isinstance(version, str):
            raise TypeError("Version must be of type string")
        if self.send_notifications:
            message_headline = "New platform-tools release"
            message_version = f"*Version*: <{version}>"
            message_release_notes = f"<{RELEASE_NOTES_URL}|Release Notes>"

            message_blocks = [
                blocks.SectionBlock(
                    text=blocks.TextObject(type="mrkdwn", text=message_headline),
                ),
                blocks.ContextBlock(
                    elements=[
                        blocks.TextObject(type="mrkdwn", text=message_version),
                        blocks.TextObject(type="mrkdwn", text=message_release_notes),
                    ]
                ),
            ]

            self.slack.chat_postMessage(
                channel=self.channel,
                blocks=message_blocks,
                text=f"Publishing platform-tools v{version}",
                unfurl_links=False,
                unfurl_media=False,
            )
