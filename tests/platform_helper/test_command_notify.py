from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dbt_platform_helper.commands.notify import add_comment
from dbt_platform_helper.commands.notify import environment_progress
from dbt_platform_helper.commands.notify import get_build_url

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
    "options, expected_text, expect_update",
    (
        ([], [], False),
        (["--slack-ref", "10000.10"], [], True),
        (["--repository", "repo1"], [EXP_REPO_TEXT % {"name": "repo1"}], False),
        (
            ["--slack-ref", "10000.10", "--repository", "repo1"],
            [EXP_REPO_TEXT % {"name": "repo1"}],
            True,
        ),
        (
            ["--repository", "repo2", "--commit-sha", "abc1234"],
            [EXP_REPO_TEXT % {"name": "repo2"}, EXP_SHA_TEXT % {"name": "repo2", "sha": "abc1234"}],
            False,
        ),
        (
            ["--slack-ref", "10000.10", "--repository", "repo2", "--commit-sha", "abc1234"],
            [EXP_REPO_TEXT % {"name": "repo2"}, EXP_SHA_TEXT % {"name": "repo2", "sha": "abc1234"}],
            True,
        ),
        (["--build-arn", BUILD_ARN], [BUILD_ARN_MESSAGE], False),
        (["--slack-ref", "10000.10", "--build-arn", BUILD_ARN], [BUILD_ARN_MESSAGE], True),
        (
            ["--repository", "repo3", "--commit-sha", "xyz1234", "--build-arn", BUILD_ARN],
            [
                EXP_REPO_TEXT % {"name": "repo3"},
                EXP_SHA_TEXT % {"name": "repo3", "sha": "xyz1234"},
                BUILD_ARN_MESSAGE,
            ],
            False,
        ),
        (
            [
                "--slack-ref",
                "10000.10",
                "--repository",
                "repo3",
                "--commit-sha",
                "xyz1234",
                "--build-arn",
                BUILD_ARN,
            ],
            [
                EXP_REPO_TEXT % {"name": "repo3"},
                EXP_SHA_TEXT % {"name": "repo3", "sha": "xyz1234"},
                BUILD_ARN_MESSAGE,
            ],
            True,
        ),
    ),
)
@patch("dbt_platform_helper.commands.notify._get_slack_client")
def test_environment_progress(
    webclient, options: list[str], expected_text: list[str], expect_update: bool
):
    CliRunner().invoke(
        environment_progress,
        [
            "my-slack-channel-id",
            "my-slack-token",
            "The very important thing everyone should know",
        ]
        + options,
    )

    post_calls = webclient().chat_postMessage.call_args_list
    update_calls = webclient().chat_update.call_args_list

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
@patch("dbt_platform_helper.commands.notify._get_slack_client")
def test_add_comment(webclient, title: str, broadcast: bool, expected_text: str):
    cli_args = [
        "my-slack-channel-id",
        "my-slack-token",
        "1234.56",
        "The comment",
    ]

    if broadcast:
        cli_args.extend(["--send-to-main-channel", "true"])
    if title:
        cli_args.extend(["--title", title])

    CliRunner().invoke(add_comment, cli_args)

    calls = webclient().chat_postMessage.call_args_list
    assert len(calls) == 1
    call_args = calls[0].kwargs
    assert call_args["channel"] == "my-slack-channel-id"
    assert call_args["text"] == expected_text
    assert call_args["reply_broadcast"] == broadcast
    assert call_args["unfurl_links"] == False
    assert call_args["unfurl_media"] == False
    assert call_args["thread_ts"] == "1234.56"
    assert call_args["blocks"][0].text.text == "The comment"
