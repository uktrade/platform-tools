# [`Dockerfile.debian`](Dockerfile.debian)

This `Dockerfile` is used to create a Docker image that supports multiple versions of Python runtimes via [`pyenv`](https://github.com/pyenv/pyenv). The `tox` configuration file determines the Python versions to be tested against.

It also has the [AWS Copilot CLI](https://aws.github.io/copilot-cli/) installed to support our pull request and regression test pipelines.

## Adding a Python version

Add the Python version(s) to `Dockerfile.debian` and `tox.ini`.

## Build and publish

This is currently a manual process.

1. Log into the `platform-tools` AWS account, navigate to Elastic Container Registry and then the debain/python repository.
1. From the View push commands page, authenticate your local Docker client with ECR.
1. Populate the repository URL into the REGISTRY environment variable using `export REGISTRY='...'`
   The URL will be in the form `123123123123.dkr.ecr.eu-west-2.amazonaws.com`
1. Run `docker buildx build --platform linux/amd64,linux/arm64 --push -t $REGISTRY/debian/python:latest -f Dockerfile.debian .`
