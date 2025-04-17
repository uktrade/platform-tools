import inspect
from unittest.mock import Mock
from unittest.mock import create_autospec
from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.notify import add_comment
from dbt_platform_helper.commands.notify import environment_progress
from dbt_platform_helper.commands.notify import post_message
from dbt_platform_helper.domain.notify import Notify
from dbt_platform_helper.domain.notify import SlackChannelNotifier
from dbt_platform_helper.providers.io import ClickIOProvider
from dbt_platform_helper.providers.slack_channel_notifier import (
    SlackChannelNotifierException,
)

BUILD_ARN = "arn:aws:codebuild:us-west-1:123456:project:my-app"
EXPECTED_ADD_COMMENT = inspect.signature(Notify.add_comment)
EXPECTED_POST_MESSAGE = inspect.signature(Notify.post_message)


class TestEnvironmentProgress:
    @patch("dbt_platform_helper.commands.notify.ClickIOProvider")
    @patch("dbt_platform_helper.commands.notify.SlackChannelNotifier")
    @patch("dbt_platform_helper.commands.notify.Notify")
    def test_success_when_calling_environment_progress(
        self,
        mock_domain,
        mock_notifier,
        mock_io,
    ):
        mock_io_instance = Mock(spec=ClickIOProvider)
        mock_io.return_value = mock_io_instance
        mock_domain_instance = create_autospec(Notify, spec_set=True)
        mock_domain.return_value = mock_domain_instance
        mock_domain_instance.post_message.return_value = "success"
        mock_notifier_instance = Mock(spec=SlackChannelNotifier)
        mock_notifier.return_value = mock_notifier_instance

        options = [
            "--slack-ref",
            "10000.10",
            "--repository",
            "repo3",
            "--commit-sha",
            "xyz1234",
            "--build-arn",
            BUILD_ARN,
        ]

        result = CliRunner().invoke(
            environment_progress,
            [
                "my-slack-channel-id",
                "my-slack-token",
                "The very important thing everyone should know",
            ]
            + options,
        )

        assert result.exit_code == 0

        mock_notifier.assert_called_once_with("my-slack-token", "my-slack-channel-id")
        mock_domain.assert_called_once_with(mock_notifier_instance)

        mock_domain_instance.post_message.assert_called_once_with(
            original_message_ref="10000.10",
            message="The very important thing everyone should know",
            build_arn=BUILD_ARN,
            repository="repo3",
            commit_sha="xyz1234",
        )
        mock_io_instance.info.assert_called_once_with("success")


class TestPostMessage:
    @patch("dbt_platform_helper.commands.notify.ClickIOProvider")
    @patch("dbt_platform_helper.commands.notify.SlackChannelNotifier")
    @patch("dbt_platform_helper.commands.notify.Notify")
    def test_success_when_calling_post_message(
        self,
        mock_domain,
        mock_notifier,
        mock_io,
    ):
        mock_io_instance = Mock(spec=ClickIOProvider)
        mock_io.return_value = mock_io_instance
        mock_domain_instance = create_autospec(Notify, spec_set=True)
        mock_domain.return_value = mock_domain_instance
        mock_domain_instance.post_message.return_value = "success"
        mock_notifier_instance = Mock(spec=SlackChannelNotifier)
        mock_notifier.return_value = mock_notifier_instance

        options = [
            "--slack-ref",
            "10000.10",
            "--repository",
            "repo3",
            "--commit-sha",
            "xyz1234",
            "--build-arn",
            BUILD_ARN,
        ]

        result = CliRunner().invoke(
            post_message,
            [
                "my-slack-channel-id",
                "my-slack-token",
                "The very important thing everyone should know",
            ]
            + options,
        )

        assert result.exit_code == 0

        mock_notifier.assert_called_once_with("my-slack-token", "my-slack-channel-id")
        mock_domain.assert_called_once_with(mock_notifier_instance)

        mock_domain_instance.post_message.assert_called_once_with(
            original_message_ref="10000.10",
            message="The very important thing everyone should know",
            build_arn=BUILD_ARN,
            repository="repo3",
            commit_sha="xyz1234",
        )
        mock_io_instance.info.assert_called_once_with("success")

    @patch("dbt_platform_helper.commands.notify.ClickIOProvider")
    @patch("dbt_platform_helper.commands.notify.Notify")
    def test_aborts_with_exception_message_when_calling_post_message(self, mock_domain, mock_io):
        mock_io_instance = Mock(spec=ClickIOProvider)
        mock_io.return_value = mock_io_instance
        mock_domain.return_value.post_message.side_effect = SlackChannelNotifierException(
            "Something went wrong"
        )

        CliRunner().invoke(
            post_message,
            [
                "my-slack-channel-id",
                "my-slack-token",
                "The very important thing everyone should know",
            ],
        )

        mock_io_instance.abort_with_error.assert_called_with("Something went wrong")


class TestAddComment:
    @patch("dbt_platform_helper.providers.slack_channel_notifier.blocks.SectionBlock")
    @patch("dbt_platform_helper.commands.notify.ClickIOProvider")
    @patch("dbt_platform_helper.commands.notify.SlackChannelNotifier")
    @patch("dbt_platform_helper.commands.notify.Notify")
    def test_success(self, mock_domain, mock_notifier, mock_io, mock_blocks):
        mock_io_instance = Mock(spec=ClickIOProvider)
        mock_io.return_value = mock_io_instance
        mock_domain_instance = create_autospec(Notify, spec_set=True)
        mock_domain.return_value = mock_domain_instance

        mock_notifier_instance = Mock(spec=SlackChannelNotifier)
        mock_notifier.return_value = mock_notifier_instance

        message = "The comment"
        mock_blocks.return_value = message

        cli_args = [
            "my-slack-channel-id",
            "my-slack-token",
            "1234.56",
            "The comment",
            "--send-to-main-channel",
            "true",
            "--title",
            "The title",
        ]

        result = CliRunner().invoke(add_comment, cli_args)

        assert result.exit_code == 0

        mock_notifier.assert_called_once_with("my-slack-token", "my-slack-channel-id")
        mock_domain.assert_called_once_with(mock_notifier_instance)

        args, kwargs = mock_domain_instance.add_comment.call_args
        EXPECTED_ADD_COMMENT.bind(None, *args, **kwargs)

        mock_domain_instance.add_comment.assert_called_once_with(
            original_message_ref="1234.56",
            message="The comment",
            title="The title",
            reply_broadcast=True,
        )

    @patch("dbt_platform_helper.commands.notify.ClickIOProvider")
    @patch("dbt_platform_helper.commands.notify.Notify")
    def test_aborts_with_exception_message(self, mock_domain, mock_io):
        mock_io_instance = Mock(spec=ClickIOProvider)
        mock_io.return_value = mock_io_instance
        mock_domain.return_value.add_comment.side_effect = SlackChannelNotifierException(
            "Something went wrong"
        )

        cli_args = [
            "my-slack-channel-id",
            "my-slack-token",
            "1234.56",
            "The comment",
            "--send-to-main-channel",
            "true",
            "--title",
            "The title",
        ]

        CliRunner().invoke(add_comment, cli_args)

        mock_io_instance.abort_with_error.assert_called_with("Something went wrong")
