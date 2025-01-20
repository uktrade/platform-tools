import boto3


class ECRProvider:
    def __init__(self, client=boto3.client("ecr")):
        self.client = client

    def get_ecr_repo_names(self):
        return [
            repo["repositoryName"]
            for repo in self.client.describe_repositories().get("repositories", {})
        ]
