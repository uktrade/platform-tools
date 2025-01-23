from boto3 import Session

from dbt_platform_helper.utils.aws import get_aws_session_or_abort


class ECRProvider:
    def __init__(self, session: Session = None):
        self.session = session
        self.client = None

    def _get_client(self):
        if not self.session:
            self.session = get_aws_session_or_abort()
        return self.session.client("ecr")

    def get_ecr_repo_names(self) -> list[str]:
        return [
            repo["repositoryName"]
            for repo in self._get_client().describe_repositories().get("repositories", {})
        ]
