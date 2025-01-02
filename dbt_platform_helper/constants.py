# Todo: Move to Config provider
PLATFORM_CONFIG_FILE = "platform-config.yml"
# Todo: Can we get rid of this yet?
PLATFORM_HELPER_VERSION_FILE = ".platform-helper-version"
# Todo: Move to ???
DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION = "5"

# Keys
CODEBASE_PIPELINES_KEY = "codebase_pipelines"
ENVIRONMENTS_KEY = "environments"

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
