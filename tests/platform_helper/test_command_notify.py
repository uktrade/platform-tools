import unittest
from unittest.mock import patch

from click.testing import CliRunner

from dbt_platform_helper.commands.notify import environment_progress
from dbt_platform_helper.commands.notify import get_build_url


@patch("dbt_platform_helper.commands.notify.get_slack_client")
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
        self.assertEqual(len(calls), 1)
        call_args = calls[0].kwargs
        self.assertEqual(call_args["channel"], "my-slack-channel-id")
        self.assertEqual(call_args["text"], "The very important thing everyone should know")
        self.assertEqual(call_args["unfurl_links"], False)
        self.assertEqual(call_args["unfurl_media"], False)
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
        self.assertEqual(len(calls), 1)
        call_args = calls[0].kwargs
        self.assertEqual(call_args["channel"], "my-slack-channel-id")
        self.assertEqual(call_args["text"], "The very important thing everyone should know")
        self.assertEqual(call_args["unfurl_links"], False)
        self.assertEqual(call_args["unfurl_media"], False)
        self.assertEqual(
            call_args["blocks"][0].text.text, "The very important thing everyone should know"
        )
        actual_elements = call_args["blocks"][1].elements
        self.assertEqual(len(actual_elements), 3)
        self.assertEqual(
            actual_elements[0].text, f"*Repository*: <https://github.com/{repository}|{repository}>"
        )
        self.assertEqual(
            actual_elements[1].text,
            f"*Revision*: <https://github.com/{repository}/commit/{commit}|{commit}>",
        )
        self.assertEqual(actual_elements[2].text, f"<{get_build_url(build_arn)}|Build Logs>")

    def test_sending_progress_updates_with_optional_build_arn(self, webclient):  # , time):
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
        self.assertEqual(len(calls), 1)
        call_args = calls[0].kwargs
        actual_elements = call_args["blocks"][1].elements
        self.assertEqual(len(actual_elements), 1)
        self.assertEqual(actual_elements[0].text, f"<{get_build_url(build_arn)}|Build Logs>")

    def test_sending_progress_updates_with_optional_repository(self, webclient):  # , time):
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
        self.assertEqual(len(calls), 1)
        call_args = calls[0].kwargs
        actual_elements = call_args["blocks"][1].elements
        self.assertEqual(len(actual_elements), 1)
        self.assertEqual(
            actual_elements[0].text, f"*Repository*: <https://github.com/{repository}|{repository}>"
        )

    def test_sending_progress_updates_with_optional_repository_and_commit(
        self, webclient
    ):  # , time):
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
        self.assertEqual(len(calls), 1)
        call_args = calls[0].kwargs
        actual_elements = call_args["blocks"][1].elements
        self.assertEqual(len(actual_elements), 2)
        self.assertEqual(
            actual_elements[0].text, f"*Repository*: <https://github.com/{repository}|{repository}>"
        )
        self.assertEqual(
            actual_elements[1].text,
            f"*Revision*: <https://github.com/{repository}/commit/{commit}|{commit}>",
        )
