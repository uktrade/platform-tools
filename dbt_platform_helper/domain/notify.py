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
        slack_ref: str = None,
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

        if slack_ref:
            return self.notifier.post_update(slack_ref, message, context)
        else:
            return self.notifier.post_new(message, context)

    def add_comment(
        self,
        original_message_ref: str,
        message: str,
        title: str,
        send_to_main_channel: bool,
    ):
        self.notifier.post_new(
            message=message,
            title=title,
            context=[],
            reply_broadcast=send_to_main_channel,
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
