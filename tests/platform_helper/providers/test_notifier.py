from unittest.mock import Mock
from unittest.mock import patch

import pytest

from dbt_platform_helper.providers.notifier import SlackChannelNotifier


class TestSlackChannelNotifier:
    @pytest.mark.parametrize(
        "slack_ref, context",
        (
            ("10000.10", None),
            ("10000.10", ["A"]),
            ("10000.10", ["A", "B"]),
        ),
    )
    @patch("dbt_platform_helper.providers.notifier.WebClient")
    def test_post_update_calls_client_with_expected_arguments(
        self,
        mock_webclient,
        slack_ref,
        context,
    ):
        mock_slack_client_instance = Mock()
        mock_webclient.return_value = mock_slack_client_instance

        SlackChannelNotifier("my-slack-token", "my-slack-channel-id").post_update(
            message="The very important thing everyone should know",
            message_ref=slack_ref,
            context=context,
        )

        mock_webclient.assert_called_with("my-slack-token")

        post_calls = mock_slack_client_instance.chat_postMessage.call_args_list
        update_calls = mock_slack_client_instance.chat_update.call_args_list

        assert len(update_calls) == 1
        assert len(post_calls) == 0

        call_args = update_calls[0].kwargs

        assert call_args["ts"] == slack_ref
        assert call_args["channel"] == "my-slack-channel-id"
        assert call_args["text"] == "The very important thing everyone should know"
        assert not call_args["unfurl_links"]
        assert not call_args["unfurl_media"]
        assert call_args["blocks"][0].text.text == "The very important thing everyone should know"

        if context:
            assert len(call_args["blocks"]) == 2
            actual_block_elements = [element.text for element in call_args["blocks"][1].elements]
            assert actual_block_elements == context
        else:
            assert len(call_args["blocks"]) == 1

    @pytest.mark.parametrize(
        "slack_ref, context, title, reply_broadcast",
        (
            (None, None, "A Title", True),
            (None, ["A"], "A Title", True),
            (None, ["A", "B"], "A Title", True),
        ),
    )
    @patch("dbt_platform_helper.providers.notifier.WebClient")
    def test_post_new_calls_client_with_expected_arguments(
        self,
        mock_webclient,
        slack_ref,
        context,
        title,
        reply_broadcast,
    ):
        mock_slack_client_instance = Mock()
        mock_webclient.return_value = mock_slack_client_instance

        SlackChannelNotifier("my-slack-token", "my-slack-channel-id").post_new(
            message="The comment",
            context=context,
            title=title,
            reply_broadcast=reply_broadcast,
            thread_ref=slack_ref,
        )

        mock_webclient.assert_called_with("my-slack-token")

        post_calls = mock_slack_client_instance.chat_postMessage.call_args_list
        update_calls = mock_slack_client_instance.chat_update.call_args_list

        assert len(post_calls) == 1
        assert len(update_calls) == 0

        call_args = post_calls[0].kwargs

        assert call_args["thread_ts"] == slack_ref
        assert call_args["channel"] == "my-slack-channel-id"
        assert call_args["text"] == "A Title"
        assert not call_args["unfurl_links"]
        assert not call_args["unfurl_media"]
        assert call_args["blocks"][0].text.text == "The comment"
        assert call_args["reply_broadcast"] == reply_broadcast

        if context:
            assert len(call_args["blocks"]) == 2
            actual_block_elements = [element.text for element in call_args["blocks"][1].elements]
            assert actual_block_elements == context
        else:
            assert len(call_args["blocks"]) == 1

    @pytest.mark.parametrize(
        "title, message, expected",
        (
            (None, "The comment", "The comment"),
            ("The title", "The comment", "The title"),
        ),
    )
    @patch("dbt_platform_helper.providers.notifier.WebClient")
    def test_post_new_text_defaults_to_message_if_no_title(
        self, mock_webclient, title, message, expected
    ):
        mock_slack_client_instance = Mock()
        mock_webclient.return_value = mock_slack_client_instance

        SlackChannelNotifier("my-slack-token", "my-slack-channel-id").post_new(
            message=message,
            title=title,
        )

        call_args = mock_slack_client_instance.chat_postMessage.call_args_list[0].kwargs
        assert call_args["text"] == expected
        assert call_args["blocks"][0].text.text == message
