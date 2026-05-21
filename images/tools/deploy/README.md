# Platform Build Tools image

Dockerfile used to build the `platform-deploy-tools` image used in GitHub workflows. Contains the `dbt-platform-helper` tool.

## Build and push via CodeBuild

This only works with the PyPI published version of `dbt-platform-helper` via the `PLATFORM_HELPER_VERSION` variable.

```shell
aws sso login
export AWS_PROFILE=platform-tools
aws codebuild start-build --project-name <...> --environment-variables-override name=PLATFORM_HELPER_VERSION,value=<...>,type=PLAINTEXT
```

aws codebuild start-build \
  --project-name your-project-name \
  --environment-variables-override \
    name=PLATFORM_HELPER_VERSION,value=15.29.0,type=PLAINTEXT

## Build and push to ECR locally

Login to public ECR

```shell
export AWS_PROFILE=platform-tools
aws sso login
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
```

Build with a released version of Platform Helper from PyPI.

```shell
#FROM repository root
DOCKER_BUILDKIT=1 docker build -f images/tools/deploy/Dockerfile --build-arg PLATFORM_HELPER_VERSION=15.29.0 -t deploy-tools . --platform linux/amd64
```

Or alternatively, build with a local version of Platform Helper.

```shell
DOCKER_BUILDKIT=1 docker build -f images/tools/deploy/Dockerfile --build-arg PLATFORM_HELPER_VERSION_OVERRIDE=true -t deploy-tools . --platform linux/amd64
```
