# Platform Build Tools image

Dockerfile used to build the `platform-deploy-tools` image used in GitHub workflows. Contains the `dbt-platform-helper` tool.

## Build and push via CodeBuild

This only works with the PyPI published version of `dbt-platform-helper` via the `PLATFORM_HELPER_VERSION` variable.

```shell
aws sso login
export AWS_PROFILE=platform-tools
PLATFORM_HELPER_VERSION=<X.X.X> aws codebuild start-build --project-name build-platform-deploy-tools --environment-variables-override name=PLATFORM_HELPER_VERSION,value=$PLATFORM_HELPER_VERSION,type=PLAINTEXT
```

## Build and push to ECR locally

Login to public ECR.

```shell
export AWS_PROFILE=platform-tools && aws sso login
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
```

Build with a released version of Platform Helper from PyPI.

```shell
#FROM repository root
DOCKER_BUILDKIT=1 PLATFORM_HELPER_VERSION=X.X.X docker build -f images/tools/deploy/Dockerfile --build-arg PLATFORM_HELPER_VERSION=$PLATFORM_HELPER_VERSION -t public.ecr.aws/uktrade/platform-deploy-tools:$PLATFORM_HELPER_VERSION . --platform linux/amd64
```

Or alternatively, build with a local version of Platform Helper. Replace `<CUSTOM_IMAGE_TAG>` with your desired testing tag (not `latest` or in the `X.X.X` release format)

```shell
DOCKER_BUILDKIT=1 docker build -f images/tools/deploy/Dockerfile --build-arg PLATFORM_HELPER_VERSION_OVERRIDE=true -t public.ecr.aws/uktrade/platform-deploy-tools:<CUSTOM_IMAGE_TAG> . --platform linux/amd64
```

Push to ECR.

```shell
docker push public.ecr.aws/uktrade/platform-deploy-tools --all-tags
```
