# Platform Deploy Tools image

Reusable Docker image used by GitHub workflows for platform ECS deployment tasks. Image is published to `public.ecr.aws/uktrade/platform-deploy-tools`. It contains:

- Platform Helper
- Terraform
- Python

## Build and push via CodeBuild

This is the recommended way to publish the image. CodeBuild only builds from a published PyPI version of `dbt-platform-helper`. Pass the desired version via the `PLATFORM_HELPER_VERSION` environment variable.

```shell
aws sso login
export AWS_PROFILE=platform-tools
aws codebuild start-build --project-name build-platform-deploy-tools --environment-variables-override name=PLATFORM_HELPER_VERSION,value=<X.X.X>,type=PLAINTEXT
```

The Codebuild job tags and pushes the image as:

```text
public.ecr.aws/uktrade/platform-deploy-tools:<X.X.X>
public.ecr.aws/uktrade/platform-deploy-tools:latest
```

## Manual build and push

Manual builds are useful for testing changes locally. All commands must be ran from the repository root.

First, login to public ECR.

```shell
aws sso login
export AWS_PROFILE=platform-tools
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
```

### Build from a PyPI release

Build the image with a released version of `dbt-platform-helper` from PyPI. Replace `PLATFORM_HELPER_VERSION` with the desired version.

```shell
PLATFORM_HELPER_VERSION=<X.X.X>
DOCKER_BUILDKIT=1 docker build --platform linux/amd64 -f images/tools/deploy/Dockerfile --build-arg PLATFORM_HELPER_VERSION=$PLATFORM_HELPER_VERSION -t public.ecr.aws/uktrade/platform-deploy-tools:$PLATFORM_HELPER_VERSION .
```

### Build from the local repository

Use this when testing local, unpublished changes to `dbt-platform-helper`.

The Dockerfile uses a BuildKit bind mount to make the local repository available during the build without copying it into the final image.

Use a custom image tag for local test builds. DO NOT use latest or release-style `X.X.X` tags!

```shell
CUSTOM_IMAGE_TAG=<CUSTOM_IMAGE_TAG>
DOCKER_BUILDKIT=1 docker build --platform linux/amd64 -f images/tools/deploy/Dockerfile --build-arg PLATFORM_HELPER_VERSION_OVERRIDE=true -t public.ecr.aws/uktrade/platform-deploy-tools:$CUSTOM_IMAGE_TAG .
```

### Push a manually built image

Push a specific tag. Avoid pushing all local tags unless you know what you are doing.

```shell
docker push "public.ecr.aws/uktrade/platform-deploy-tools:<TAG>"
```

## Test locally

Run the image with an interactive shell.

```shell
docker run --rm -it public.ecr.aws/uktrade/platform-deploy-tools:<TAG>
```

Check the tools installed in the image.

```shell
docker run --rm public.ecr.aws/uktrade/platform-deploy-tools:<TAG> terraform version
docker run --rm public.ecr.aws/uktrade/platform-deploy-tools:<TAG> platform-helper --help
```
