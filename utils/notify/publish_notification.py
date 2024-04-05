import argparse
import os

from slack_sdk import WebClient
from slack_sdk.models import blocks

RELEASE_NOTES_URL = "https://github.com/uktrade/platform-tools/releases/latest"
OK = 0


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


def opts():
    parser = argparse.ArgumentParser(
        description="Sends a notification about a new release of platform-helper to Slack"
    )
    parser.add_argument(
        "--send-notifications", help="Enables/disables notifications", type=bool, default=True
    )
    parser.add_argument(
        "--publish-version", help="Specifies the published version", type=str, default=None
    )
    return parser.parse_args()


def send_publish_notification_version(options):
    notifier = PublishNotify(options.send_notifications)
    notifier.post_publish_update(options.publish_version)
    return OK


if __name__ == "__main__":
    exit(send_publish_notification_version(opts()))
