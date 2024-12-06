# Todo: Move to Config provider
PLATFORM_CONFIG_FILE = "platform-config.yml"
# Todo: Can we get rid of this yet?
PLATFORM_HELPER_VERSION_FILE = ".platform-helper-version"
# Todo: Move to ???
DEFAULT_TERRAFORM_PLATFORM_MODULES_VERSION = "5"
# Todo: Move to cache provider
PLATFORM_HELPER_CACHE_FILE = ".platform-helper-config-cache.yml"

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
