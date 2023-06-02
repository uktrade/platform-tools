import boto3
import botocore


def check_aws_conn(aws_profile):
    # Check that the aws profile exists and is set.
    print("Checking AWS connection...")

    try:
        session = boto3.session.Session(profile_name=aws_profile)
    except botocore.exceptions.ProfileNotFound:
        print("AWS profile not configured, please ensure they are set.")
        exit()
    except botocore.errorfactory.UnauthorizedException:
        print(
            "The SSO session associated with this profile has expired or is otherwise invalid.",
            "To refresh this SSO session run aws sso login with the corresponding profile",
        )
        exit()

    sts = session.client("sts")
    try:
        sts.get_caller_identity()
        print("Credentials are valid.")
    except botocore.exceptions.SSOTokenLoadError:
        print(f"Credentials are NOT valid.  \nPlease login with: aws sso login --profile {aws_profile}")
        exit()
    except botocore.exceptions.UnauthorizedSSOTokenError:
        print(
            "The SSO session associated with this profile has expired or is otherwise invalid.\
              To refresh this SSO session run aws sso login with the corresponding profile"
        )
        exit()

    alias_client = session.client("iam")
    account_name = alias_client.list_account_aliases()["AccountAliases"]
    print(
        f"Logged in with AWS Domain account: {account_name[0]}/{sts.get_caller_identity()['Account']}\n\
          User: {sts.get_caller_identity()['UserId']}"
    )
    return session


def check_response(response):
    if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
        print(f"Unknown response error from AWS.\nStatus Code: {response['ResponseMetadata']['HTTPStatusCode']}")
        exit()
