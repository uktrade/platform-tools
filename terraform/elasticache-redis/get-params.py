import boto3

session = boto3.Session(profile_name="intranet")

client = session.client("ssm")

path = "/copilot/intranet/staging/"

response = client.get_parameters_by_path(
    Path=path,
    WithDecryption=True,
    MaxResults=150,
    # NextToken='string'
)
