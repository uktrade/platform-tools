import argparse
import os
import re
import subprocess

RELEASE_NOTES_URL_LATEST = "https://github.com/uktrade/platform-tools/releases/latest"
RELEASE_NOTES_URL_TAG = "https://github.com/uktrade/platform-tools/releases/tag/"
OK = 0


class PublishNotify:

    def __init__(self, send_notifications: bool = True):
        self.send_notifications = send_notifications

        if self.send_notifications:
            try:
                self.slack_token = os.environ["SLACK_TOKEN"]
                self.channel = os.environ["SLACK_CHANNEL_ID"]
            except KeyError as e:
                raise ValueError(f"{e} environment variable must be set")

    def post_publish_update(self, version: str):
        if not isinstance(version, str):
            raise TypeError("Version must be of type string")
        if self.send_notifications:
            message_headline = "New `platform-helper` release"
            message_version = f"*Version*: {version}"
            if validate_version_pattern(version):
                message_release_notes = f"<{RELEASE_NOTES_URL_TAG}{version}|Release Notes>"
            else:
                message_release_notes = f"<{RELEASE_NOTES_URL_LATEST}|Release Notes>"

            message = f":tada: {message_headline} - {message_version} - {message_release_notes}"

            self.notify_slack(self.channel, self.slack_token, message)

    def notify_slack(self, channel, token, message):
        try:
            subprocess.run(
                ["platform-helper", "notify", "add-comment", channel, token, "", message],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"Failed to send notification: {e}")


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


def validate_version_pattern(string: str) -> bool:
    pattern = re.compile(r"^([0-9]+\.[0-9]+\.[0-9]+)$")
    if pattern.match(string):
        return True
    return False


if __name__ == "__main__":
    exit(send_publish_notification_version(opts()))
