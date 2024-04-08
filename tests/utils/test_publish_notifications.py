import os
import unittest
from unittest.mock import patch

import pytest
from parameterized import parameterized
from slack_sdk.models import blocks

from tests.test_doubles.webclient import WebClient
from utils.notify.publish_notification import RELEASE_NOTES_URL
from utils.notify.publish_notification import PublishNotify
from utils.notify.publish_notification import send_publish_notification_version


class FakeOpts:
    def __init__(self, **data):
        self.__dict__ = data


@patch("builtins.round", return_value=15)
@patch("utils.notify.publish_notification.WebClient", return_value=WebClient("slack-token"))
class TestPublishNotify(unittest.TestCase):
    def setUp(self):
        os.environ["SLACK_TOKEN"] = "slack-token"
        os.environ["SLACK_CHANNEL_ID"] = "channel-id"
        self.version = "0.0.0"

    @parameterized.expand(
        [
            ("SLACK_TOKEN",),
            ("SLACK_CHANNEL_ID",),
        ]
    )
    def test_raises_error_when_environment_not_set(self, webclient, time, environment_variable):
        del os.environ[environment_variable]
        with pytest.raises(ValueError) as e:
            PublishNotify()
        self.assertEqual(f"'{environment_variable}' environment variable must be set", str(e.value))

    def test_sending_publish_notifications_when_notifications_off(self, webclient, time):
        notify = PublishNotify(False)
        notify.post_publish_update(self.version)

        self.assertFalse(hasattr(notify, "slack"))

    def test_sending_publish_notifications_successfully(self, webclient, time):
        notify = PublishNotify()
        notify.post_publish_update(self.version)

        notify.slack.chat_postMessage.assert_called_with(
            channel="channel-id",
            blocks=get_expected_message_blocks(self.version),
            text=f"Publishing platform-helper v{self.version}",
            unfurl_links=False,
            unfurl_media=False,
        )

    def test_send_publish_notification_version_from_cli(self, webclient, time):
        opts = FakeOpts(send_notifications=True, publish_version=self.version)
        exit_code = send_publish_notification_version(opts)
        assert exit_code == 0

    def test_version_provided_must_be_a_string(self, webclient, time):
        with pytest.raises(TypeError):
            notify = PublishNotify()
            notify.post_publish_update(True)

        with pytest.raises(TypeError):
            notify = PublishNotify()
            notify.post_publish_update(123)


def get_expected_message_blocks(version=""):
    return [
        blocks.SectionBlock(
            text=blocks.TextObject(
                type="mrkdwn",
                text="New platform-helper release",
            )
        ),
        blocks.ContextBlock(
            elements=[
                blocks.TextObject(
                    type="mrkdwn",
                    text=f"*Version*: <{version}>",
                ),
                blocks.TextObject(
                    type="mrkdwn",
                    text=f"<{RELEASE_NOTES_URL}|Release Notes>",
                ),
            ]
        ),
    ]