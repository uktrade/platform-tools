from unittest.mock import Mock

import pytest

from dbt_platform_helper.domain.notify import Notify
from dbt_platform_helper.domain.notify import SlackClient
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
            [EXP_REPO_TEXT % {"name": "repo2"}, EXP_SHA_TEXT % {"name": "repo2", "sha": "abc1234"}],
            False,
        ),
        (
            "10000.10",
            "repo2",
            "abc1234",
            None,
            [EXP_REPO_TEXT % {"name": "repo2"}, EXP_SHA_TEXT % {"name": "repo2", "sha": "abc1234"}],
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
    slack_ref, repository, sha, build_arn, expected_text: list[str], expect_update: bool
):
    mock_slack_client = Mock(spec=SlackClient)
    mock_slack_client.slack_channel_id = "my-slack-channel-id"
    mock_slack_client.slack_token = "my-slack-token"

    Notify(mock_slack_client).environment_progress(
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
def test_add_comment(title: str, broadcast: bool, expected_text: str):
    mock_slack_client = Mock(spec=SlackClient)
    mock_slack_client.slack_channel_id = "my-slack-channel-id"
    mock_slack_client.slack_token = "my-slack-token"
    slack_ref = "1234.56"

    Notify(mock_slack_client).add_comment(
        slack_ref, message="The comment", title=title, send_to_main_channel=broadcast
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


# TODO add a test for the slack client to ensure the webclient is correctly set, or maybe just remove the SlackClient wrapper
