from unittest.mock import Mock
from unittest.mock import patch

import pytest

from dbt_platform_helper.domain.notify import Notify
from dbt_platform_helper.domain.notify import SlackChannelNotifier
from dbt_platform_helper.domain.notify import get_build_url

BUILD_ARN = "arn:aws:codebuild:us-west-1:123456:project:my-app"
BUILD_ARN_MESSAGE = f"<{get_build_url(BUILD_ARN)}|Build Logs>"
EXP_REPO_TEXT = "*Repository*: <https://github.com/%(name)s|%(name)s>"
EXP_SHA_TEXT = "*Revision*: <https://github.com/%(name)s/commit/%(sha)s|%(sha)s>"


def test_getting_build_url():
    actual_url = get_build_url(
        "arn:aws:codebuild:region:000000000000:build/project:example-build-id"
    )
    exp_url = "https://region.console.aws.amazon.com/codesuite/codebuild/000000000000/projects/project/build/project%3Aexample-build-id"
    assert actual_url == exp_url


class TestSlackChannelNotifier:
    @pytest.mark.parametrize(
        "slack_ref, context",
        (
            ("10000.10", None),
            ("10000.10", ["A"]),
            ("10000.10", ["A", "B"]),
        ),
    )
    @patch("dbt_platform_helper.domain.notify.WebClient")
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
    @patch("dbt_platform_helper.domain.notify.WebClient")
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

    @patch("dbt_platform_helper.domain.notify.WebClient")
    def test_post_new_text_defaults_to_message_if_no_title(
        self,
        mock_webclient,
    ):
        mock_slack_client_instance = Mock()
        mock_webclient.return_value = mock_slack_client_instance

        SlackChannelNotifier("my-slack-token", "my-slack-channel-id").post_new(
            message="The comment",
            title=None,
        )

        call_args = mock_slack_client_instance.chat_postMessage.call_args_list[0].kwargs
        assert call_args["text"] == "The comment"


class TestNotify:
    @pytest.mark.parametrize(
        "slack_ref, repository, sha, build_arn, expected_context, expect_update",
        (
            (None, None, None, None, [], False),
            ("10000.10", None, None, None, [], True),
            (None, "repo1", None, None, [EXP_REPO_TEXT % {"name": "repo1"}], False),
            (
                "10000.10",
                "repo1",
                None,
                None,
                [EXP_REPO_TEXT % {"name": "repo1"}],
                True,
            ),
            (
                None,
                "repo2",
                "abc1234",
                None,
                [
                    EXP_REPO_TEXT % {"name": "repo2"},
                    EXP_SHA_TEXT % {"name": "repo2", "sha": "abc1234"},
                ],
                False,
            ),
            (
                "10000.10",
                "repo2",
                "abc1234",
                None,
                [
                    EXP_REPO_TEXT % {"name": "repo2"},
                    EXP_SHA_TEXT % {"name": "repo2", "sha": "abc1234"},
                ],
                True,
            ),
            (None, None, None, BUILD_ARN, [BUILD_ARN_MESSAGE], False),
            ("10000.10", None, None, BUILD_ARN, [BUILD_ARN_MESSAGE], True),
            (
                None,
                "repo3",
                "xyz1234",
                BUILD_ARN,
                [
                    EXP_REPO_TEXT % {"name": "repo3"},
                    EXP_SHA_TEXT % {"name": "repo3", "sha": "xyz1234"},
                    BUILD_ARN_MESSAGE,
                ],
                False,
            ),
            (
                "10000.10",
                "repo3",
                "xyz1234",
                BUILD_ARN,
                [
                    EXP_REPO_TEXT % {"name": "repo3"},
                    EXP_SHA_TEXT % {"name": "repo3", "sha": "xyz1234"},
                    BUILD_ARN_MESSAGE,
                ],
                True,
            ),
        ),
    )
    def test_environment_progress(
        self,
        slack_ref,
        repository,
        sha,
        build_arn,
        expected_context,
        expect_update,
    ):
        mock_notifier = Mock(spec=SlackChannelNotifier)

        Notify(mock_notifier).environment_progress(
            message="The very important thing everyone should know",
            slack_ref=slack_ref,
            repository=repository,
            commit_sha=sha,
            build_arn=build_arn,
        )

        if expect_update:
            mock_notifier.post_update.assert_called_with(
                slack_ref, "The very important thing everyone should know", expected_context
            )
        else:
            mock_notifier.post_new.assert_called_with(
                "The very important thing everyone should know",
                expected_context,
            )

    @pytest.mark.parametrize(
        "title, broadcast",
        (
            (None, False),
            (None, True),
            ("My title", False),
            ("My title", True),
        ),
    )
    def test_add_comment(self, title: str, broadcast: bool):
        mock_slack_notifier = Mock(spec=SlackChannelNotifier)

        Notify(mock_slack_notifier).add_comment(
            "1234.56", message="The comment", title=title, send_to_main_channel=broadcast
        )

        mock_slack_notifier.post_new.assert_called_once_with(
            message="The comment",
            title=title,
            context=[],
            reply_broadcast=broadcast,
            thread_ref="1234.56",
        )


class TestNotifyE2E:
    @pytest.mark.parametrize(
        "slack_ref, repository, sha, build_arn, expected_text, expect_update",
        (
            (None, None, None, None, [], False),
            ("10000.10", None, None, None, [], True),
            (None, "repo1", None, None, [EXP_REPO_TEXT % {"name": "repo1"}], False),
            (
                "10000.10",
                "repo1",
                None,
                None,
                [EXP_REPO_TEXT % {"name": "repo1"}],
                True,
            ),
            (
                None,
                "repo2",
                "abc1234",
                None,
                [
                    EXP_REPO_TEXT % {"name": "repo2"},
                    EXP_SHA_TEXT % {"name": "repo2", "sha": "abc1234"},
                ],
                False,
            ),
            (
                "10000.10",
                "repo2",
                "abc1234",
                None,
                [
                    EXP_REPO_TEXT % {"name": "repo2"},
                    EXP_SHA_TEXT % {"name": "repo2", "sha": "abc1234"},
                ],
                True,
            ),
            (None, None, None, BUILD_ARN, [BUILD_ARN_MESSAGE], False),
            ("10000.10", None, None, BUILD_ARN, [BUILD_ARN_MESSAGE], True),
            (
                None,
                "repo3",
                "xyz1234",
                BUILD_ARN,
                [
                    EXP_REPO_TEXT % {"name": "repo3"},
                    EXP_SHA_TEXT % {"name": "repo3", "sha": "xyz1234"},
                    BUILD_ARN_MESSAGE,
                ],
                False,
            ),
            (
                "10000.10",
                "repo3",
                "xyz1234",
                BUILD_ARN,
                [
                    EXP_REPO_TEXT % {"name": "repo3"},
                    EXP_SHA_TEXT % {"name": "repo3", "sha": "xyz1234"},
                    BUILD_ARN_MESSAGE,
                ],
                True,
            ),
        ),
    )
    @patch("dbt_platform_helper.domain.notify.WebClient")
    def test_environment_progress(
        self,
        mock_slack_client,
        slack_ref,
        repository,
        sha,
        build_arn,
        expected_text: list[str],
        expect_update: bool,
    ):
        slack_notifier = SlackChannelNotifier("my-slack-token", "my-slack-channel-id")
        slack_notifier.client = mock_slack_client

        Notify(slack_notifier).environment_progress(
            message="The very important thing everyone should know",
            slack_ref=slack_ref,
            repository=repository,
            commit_sha=sha,
            build_arn=build_arn,
        )

        post_calls = mock_slack_client.chat_postMessage.call_args_list
        update_calls = mock_slack_client.chat_update.call_args_list

        if expect_update:
            calls = update_calls
            zero_calls = post_calls
        else:
            calls = post_calls
            zero_calls = update_calls

        assert len(calls) == 1
        assert len(zero_calls) == 0

        call_args = calls[0].kwargs
        assert call_args["channel"] == "my-slack-channel-id"
        assert call_args["text"] == "The very important thing everyone should know"
        assert not call_args["unfurl_links"]
        assert not call_args["unfurl_media"]
        assert call_args["blocks"][0].text.text == "The very important thing everyone should know"

        if expected_text:
            actual_elements = call_args["blocks"][1].elements
            assert len(actual_elements) == len(expected_text)
            for element, exp_text in zip(actual_elements, expected_text):
                assert element.text == exp_text

    @pytest.mark.parametrize(
        "title, broadcast, expected_text",
        (
            (None, False, "The comment"),
            (None, True, "The comment"),
            ("My title", False, "My title"),
            ("My title", True, "My title"),
        ),
    )
    @patch("dbt_platform_helper.domain.notify.WebClient")
    def test_add_comment(self, mock_slack_client, title: str, broadcast: bool, expected_text: str):
        slack_notifier = SlackChannelNotifier("token", "my-slack-channel-id")
        slack_notifier.client = mock_slack_client

        Notify(slack_notifier).add_comment(
            "1234.56", message="The comment", title=title, send_to_main_channel=broadcast
        )

        calls = mock_slack_client.chat_postMessage.call_args_list
        assert len(calls) == 1
        call_args = calls[0].kwargs
        assert call_args["channel"] == "my-slack-channel-id"
        assert call_args["text"] == expected_text
        assert call_args["reply_broadcast"] == broadcast
        assert call_args["unfurl_links"] == False
        assert call_args["unfurl_media"] == False
        assert call_args["thread_ts"] == "1234.56"
        assert call_args["blocks"][0].text.text == "The comment"
