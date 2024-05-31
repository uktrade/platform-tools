import unittest
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dbt_platform_helper.commands.notify import add_comment
from dbt_platform_helper.commands.notify import environment_progress
from dbt_platform_helper.commands.notify import get_build_url


@patch("dbt_platform_helper.commands.notify._get_slack_client")
class TestNotify(unittest.TestCase):
    def test_getting_build_url(self, webclient):
        self.assertEqual(
            get_build_url("arn:aws:codebuild:region:000000000000:build/project:example-build-id"),
            "https://region.console.aws.amazon.com/codesuite/codebuild/000000000000"
            "/projects/project/build/project%3Aexample-build-id",
        )

    def test_sending_progress_updates_with_no_optional_elements(self, webclient):
        CliRunner().invoke(
            environment_progress,
            [
                "my-slack-channel-id",
                "my-slack-token",
                "The very important thing everyone should know",
            ],
        )

        calls = webclient().chat_postMessage.call_args_list
        assert len(calls) == 1
        call_args = calls[0].kwargs
        assert call_args["channel"] == "my-slack-channel-id"
        assert call_args["text"] == "The very important thing everyone should know"
        assert call_args["unfurl_links"] == False
        assert call_args["unfurl_media"] == False
        self.assertEqual(
            call_args["blocks"][0].text.text, "The very important thing everyone should know"
        )

    def test_sending_progress_updates_with_all_optional_elements(self, webclient):
        build_arn = "arn:aws:codebuild:us-west-1:123456:project:my-app"
        repository = "my-repo"
        commit = "abc1234"
        CliRunner().invoke(
            environment_progress,
            [
                "my-slack-channel-id",
                "my-slack-token",
                "The very important thing everyone should know",
                "--build-arn",
                build_arn,
                "--repository",
                repository,
                "--commit-sha",
                commit,
            ],
        )
        calls = webclient().chat_postMessage.call_args_list
        assert len(calls) == 1
        call_args = calls[0].kwargs
        assert call_args["channel"] == "my-slack-channel-id"
        assert call_args["text"] == "The very important thing everyone should know"
        assert call_args["unfurl_links"] == False
        assert call_args["unfurl_media"] == False
        self.assertEqual(
            call_args["blocks"][0].text.text, "The very important thing everyone should know"
        )
        actual_elements = call_args["blocks"][1].elements
        assert len(actual_elements) == 3
        self.assertEqual(
            actual_elements[0].text, f"*Repository*: <https://github.com/{repository}|{repository}>"
        )
        self.assertEqual(
            actual_elements[1].text,
            f"*Revision*: <https://github.com/{repository}/commit/{commit}|{commit}>",
        )
        assert actual_elements[2].text == f"<{get_build_url(build_arn)}|Build Logs>"

    def test_sending_progress_updates_with_optional_build_arn(self, webclient):
        build_arn = "arn:aws:codebuild:us-west-1:123456:project:my-app"
        CliRunner().invoke(
            environment_progress,
            [
                "my-slack-channel-id",
                "my-slack-token",
                "The very important thing everyone should know",
                "--build-arn",
                build_arn,
            ],
        )
        calls = webclient().chat_postMessage.call_args_list
        assert len(calls) == 1
        call_args = calls[0].kwargs
        actual_elements = call_args["blocks"][1].elements
        assert len(actual_elements) == 1
        assert actual_elements[0].text == f"<{get_build_url(build_arn)}|Build Logs>"

    def test_sending_progress_updates_with_optional_repository(self, webclient):
        repository = "my-repo"
        CliRunner().invoke(
            environment_progress,
            [
                "my-slack-channel-id",
                "my-slack-token",
                "The very important thing everyone should know",
                "--repository",
                repository,
            ],
        )
        calls = webclient().chat_postMessage.call_args_list
        assert len(calls) == 1
        call_args = calls[0].kwargs
        actual_elements = call_args["blocks"][1].elements
        assert len(actual_elements) == 1
        self.assertEqual(
            actual_elements[0].text, f"*Repository*: <https://github.com/{repository}|{repository}>"
        )

    def test_sending_progress_updates_with_optional_repository_and_commit(self, webclient):
        repository = "my-repo"
        commit = "abc1234"
        CliRunner().invoke(
            environment_progress,
            [
                "my-slack-channel-id",
                "my-slack-token",
                "The very important thing everyone should know",
                "--repository",
                repository,
                "--commit-sha",
                commit,
            ],
        )
        calls = webclient().chat_postMessage.call_args_list
        assert len(calls) == 1
        call_args = calls[0].kwargs
        actual_elements = call_args["blocks"][1].elements
        assert len(actual_elements) == 2
        self.assertEqual(
            actual_elements[0].text, f"*Repository*: <https://github.com/{repository}|{repository}>"
        )
        self.assertEqual(
            actual_elements[1].text,
            f"*Revision*: <https://github.com/{repository}/commit/{commit}|{commit}>",
        )

    def test_sending_progress_updates_with_optional_slack_ref(self, webclient):
        build_arn = "arn:aws:codebuild:us-west-1:123456:project:my-app"
        repository = "my-repo"
        commit = "abc1234"
        CliRunner().invoke(
            environment_progress,
            [
                "my-slack-channel-id",
                "my-slack-token",
                "The very important thing everyone should know",
                "--build-arn",
                build_arn,
                "--repository",
                repository,
                "--commit-sha",
                commit,
                "--slack-ref",
                "10000.10",
            ],
        )
        post_calls = webclient().chat_postMessage.call_args_list
        update_calls = webclient().chat_update.call_args_list
        assert len(post_calls) == 0
        assert len(update_calls) == 1

        call_args = update_calls[0].kwargs
        assert call_args["channel"] == "my-slack-channel-id"
        assert call_args["text"] == "The very important thing everyone should know"
        assert call_args["unfurl_links"] == False
        assert call_args["unfurl_media"] == False
        assert call_args["ts"] == "10000.10"
        self.assertEqual(
            call_args["blocks"][0].text.text, "The very important thing everyone should know"
        )
        actual_elements = call_args["blocks"][1].elements
        assert len(actual_elements) == 3
        self.assertEqual(
            actual_elements[0].text, f"*Repository*: <https://github.com/{repository}|{repository}>"
        )
        self.assertEqual(
            actual_elements[1].text,
            f"*Revision*: <https://github.com/{repository}/commit/{commit}|{commit}>",
        )
        assert actual_elements[2].text == f"<{get_build_url(build_arn)}|Build Logs>"


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
def test_adding_comments_no_options_set(webclient, title, broadcast, expected_text):
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
