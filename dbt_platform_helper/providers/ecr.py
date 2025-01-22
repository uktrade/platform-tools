import boto3


class ECRProvider:
    def __init__(self, client=None):
        self.client = client or boto3.client("ecr")

    def get_ecr_repo_names(self):
        return [
            repo["repositoryName"]
            for repo in self.client.describe_repositories().get("repositories", {})
        ]
