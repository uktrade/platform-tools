import os
import unittest
from unittest.mock import patch

import pytest
from parameterized import parameterized

from utils.notify.publish_notification import RELEASE_NOTES_URL_LATEST
from utils.notify.publish_notification import RELEASE_NOTES_URL_TAG
from utils.notify.publish_notification import PublishNotify
from utils.notify.publish_notification import send_publish_notification_version
from utils.notify.publish_notification import validate_version_pattern


class FakeOpts:
    def __init__(self, **data):
        self.__dict__ = data


@patch("subprocess.run")
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
    def test_raises_error_when_environment_not_set(self, mock_subprocess, environment_variable):
        del os.environ[environment_variable]
        with pytest.raises(ValueError) as e:
            PublishNotify()
        self.assertEqual(f"'{environment_variable}' environment variable must be set", str(e.value))

    def test_sending_publish_notifications_when_notifications_off(self, mock_subprocess):
        notify = PublishNotify(False)
        notify.post_publish_update(self.version)
        mock_subprocess.assert_not_called()

    def test_sending_publish_notifications_successfully_with_valid_version_format(
        self, mock_subprocess
    ):
        notify = PublishNotify()
        notify.post_publish_update(self.version)

        expected_message = (
            f":tada: New `platform-helper` release\n\n*Version*: {self.version}\n\n"
            f"<{RELEASE_NOTES_URL_TAG}{self.version}|Release Notes>"
        )

        mock_subprocess.assert_called_with(
            [
                "platform-helper",
                "notify",
                "add-comment",
                "channel-id",
                "slack-token",
                "",
                expected_message,
            ],
            check=True,
        )

    def test_sending_publish_notifications_successfully_with_invalid_version_format(
        self, mock_subprocess
    ):
        invalid_version = "1.2"
        notify = PublishNotify()
        notify.post_publish_update(invalid_version)

        expected_message = (
            f":tada: New `platform-helper` release\n\n*Version*: {invalid_version}\n\n"
            f"<{RELEASE_NOTES_URL_LATEST}|Release Notes>"
        )

        mock_subprocess.assert_called_with(
            [
                "platform-helper",
                "notify",
                "add-comment",
                "channel-id",
                "slack-token",
                "",
                expected_message,
            ],
            check=True,
        )

    def test_send_publish_notification_version_from_cli(self, mock_subprocess):
        opts = FakeOpts(send_notifications=True, publish_version=self.version)
        exit_code = send_publish_notification_version(opts)
        assert exit_code == 0

    def test_version_provided_must_be_a_string(self, mock_subprocess):
        with pytest.raises(TypeError):
            notify = PublishNotify()
            notify.post_publish_update(True)

        with pytest.raises(TypeError):
            notify = PublishNotify()
            notify.post_publish_update(123)

    def test_check_version_pattern_valid_pattern(self, mock_subprocess):
        version = "1.2.3"
        assert validate_version_pattern(version)

    def test_check_version_pattern_invalid_pattern(self, mock_subprocess):
        version = "1.2"
        assert not validate_version_pattern(version)


if __name__ == "__main__":
    unittest.main()
