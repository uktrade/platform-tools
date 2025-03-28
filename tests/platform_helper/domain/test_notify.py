from unittest.mock import Mock

import pytest

from dbt_platform_helper.domain.notify import Notify
from dbt_platform_helper.domain.notify import get_build_url
from dbt_platform_helper.providers.notifier import SlackChannelNotifier

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
