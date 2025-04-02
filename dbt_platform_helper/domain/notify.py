from dbt_platform_helper.platform_exception import PlatformException
from dbt_platform_helper.providers.notifier import SlackChannelNotifier
from dbt_platform_helper.utils.arn_parser import ARN


class Notify:
    def __init__(self, notifier: SlackChannelNotifier):
        self.notifier = notifier

    def environment_progress(
        self,
        message: str,
        build_arn: str = None,
        repository: str = None,
        commit_sha: str = None,
        original_message_ref: str = None,
    ):
        context = []

        if repository:
            context.append(f"*Repository*: <https://github.com/{repository}|{repository}>")
            if commit_sha:
                context.append(
                    f"*Revision*: <https://github.com/{repository}/commit/{commit_sha}|{commit_sha}>"
                )

        if build_arn:
            context.append(f"<{get_build_url(build_arn)}|Build Logs>")

        if original_message_ref:
            response = self.notifier.post_update(original_message_ref, message, context)
        else:
            response = self.notifier.post_new(message, context)

        try:
            return response["ts"]
        except (KeyError, TypeError):
            raise PlatformException(
                f"Slack environment progress notification unsuccessful: {response}"
            )

    def add_comment(
        self,
        original_message_ref: str,
        message: str,
        title: str,
        reply_broadcast: bool,
    ):
        self.notifier.post_new(
            message=message,
            title=title,
            context=[],
            reply_broadcast=reply_broadcast,
            thread_ref=original_message_ref,
        )


# This utility probably belongs somewhere else
def get_build_url(build_arn: str):
    try:
        arn = ARN(build_arn)
        url = (
            "https://{region}.console.aws.amazon.com/codesuite/codebuild/{account}/projects/{"
            "project}/build/{project}%3A{build_id}"
        )
        return url.format(
            region=arn.region,
            account=arn.account_id,
            project=arn.project.replace("build/", ""),
            build_id=arn.build_id,
        )
    except ValueError:
        return ""
