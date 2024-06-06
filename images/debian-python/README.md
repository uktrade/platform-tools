# [`Dockerfile.debian`](Dockerfile.debian)

This `Dockerfile` is used to create a Docker image that supports multiple versions of Python runtimes via [`pyenv`](https://github.com/pyenv/pyenv). The `tox` configuration file determines the Python versions to be tested against.

It also has the [AWS Copilot CLI](https://aws.github.io/copilot-cli/) installed to support our pull request and regression test pipelines.

## Adding a Python version

Add the Python version(s) to `Dockerfile.debian` and `tox.ini`.

## Build and publish

This is currently a manual process.

Run `docker build -f Dockerfile.debian -t debian/python .` to build the image.

For Platform developers, the `push` commands can be found in [AWS ECR](https://eu-west-2.console.aws.amazon.com/ecr/repositories).
