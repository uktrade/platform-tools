# TODO: DBTP-1888: Move to Config provider
PLATFORM_CONFIG_FILE = "platform-config.yml"
# TODO: DBTP-1950: Can we get rid of this yet?
PLATFORM_HELPER_VERSION_FILE = ".platform-helper-version"
SUPPORTED_TERRAFORM_VERSION = "~> 1.8"
SUPPORTED_AWS_PROVIDER_VERSION = "~> 5"

MERGED_TPM_PLATFORM_HELPER_VERSION = 14

# Keys
CODEBASE_PIPELINES_KEY = "codebase_pipelines"
ENVIRONMENTS_KEY = "environments"
ENVIRONMENT_PIPELINES_KEY = "environment_pipelines"

# Conduit
CONDUIT_ADDON_TYPES = [
    "opensearch",
    "postgres",
    "redis",
]
CONDUIT_DOCKER_IMAGE_LOCATION = "public.ecr.aws/uktrade/tunnel"
HYPHENATED_APPLICATION_NAME = "hyphenated-application-name"
ALPHANUMERIC_ENVIRONMENT_NAME = "alphanumericenvironmentname123"
ALPHANUMERIC_SERVICE_NAME = "alphanumericservicename123"
COPILOT_IDENTIFIER = "c0PIlotiD3ntIF3r"
CLUSTER_NAME_SUFFIX = f"Cluster-{COPILOT_IDENTIFIER}"
SERVICE_NAME_SUFFIX = f"Service-{COPILOT_IDENTIFIER}"
REFRESH_TOKEN_MESSAGE = (
    "To refresh this SSO session run `aws sso login` with the corresponding profile"
)
