from unittest.mock import Mock
from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.notify import add_comment
from dbt_platform_helper.commands.notify import environment_progress
from dbt_platform_helper.domain.notify import Notify
from dbt_platform_helper.domain.notify import SlackChannelNotifier
from dbt_platform_helper.providers.io import ClickIOProvider

BUILD_ARN = "arn:aws:codebuild:us-west-1:123456:project:my-app"


@patch("dbt_platform_helper.commands.notify.ClickIOProvider")
@patch("dbt_platform_helper.commands.notify.SlackChannelNotifier")
@patch("dbt_platform_helper.commands.notify.Notify")
def test_environment_progress(
    mock_domain,
    mock_notifier,
    mock_io,
):
    mock_io_instance = Mock(spec=ClickIOProvider)
    mock_io.return_value = mock_io_instance
    mock_domain_instance = Mock(spec=Notify)
    mock_domain.return_value = mock_domain_instance
    mock_domain_instance.environment_progress.return_value = {"ts": "success"}
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

    CliRunner().invoke(
        environment_progress,
        [
            "my-slack-channel-id",
            "my-slack-token",
            "The very important thing everyone should know",
        ]
        + options,
    )

    mock_notifier.assert_called_once_with("my-slack-token", "my-slack-channel-id")
    mock_domain.assert_called_once_with(mock_notifier_instance)
    mock_domain_instance.environment_progress.assert_called_once_with(
        slack_ref="10000.10",
        message="The very important thing everyone should know",
        build_arn=BUILD_ARN,
        repository="repo3",
        commit_sha="xyz1234",
    )
    mock_io_instance.info.assert_called_once_with("success")


@patch("dbt_platform_helper.commands.notify.blocks.SectionBlock")
@patch("dbt_platform_helper.commands.notify.ClickIOProvider")
@patch("dbt_platform_helper.commands.notify.SlackChannelNotifier")
@patch("dbt_platform_helper.commands.notify.Notify")
def test_add_comment(mock_domain, mock_notifier, mock_io, mock_blocks):
    mock_io_instance = Mock(spec=ClickIOProvider)
    mock_io.return_value = mock_io_instance
    mock_domain_instance = Mock(spec=Notify)
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

    CliRunner().invoke(add_comment, cli_args)

    mock_notifier.assert_called_once_with("my-slack-token", "my-slack-channel-id")
    mock_domain.assert_called_once_with(mock_notifier_instance)
    mock_domain_instance.add_comment.assert_called_once_with(
        blocks=["The comment"],
        text="The title",
        reply_broadcast=True,
        unfurl_links=False,
        unfurl_media=False,
        thread_ts="1234.56",
    )
