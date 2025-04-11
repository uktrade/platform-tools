from dbt_platform_helper.providers.slack_channel_notifier import SlackChannelNotifier
from dbt_platform_helper.utils.arn_parser import ARN


class Notify:
    def __init__(self, notifier: SlackChannelNotifier):
        self.notifier = notifier

    def post_message(
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
            return self.notifier.post_update(original_message_ref, message, context)
        else:
            return self.notifier.post_new(message, context)

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
