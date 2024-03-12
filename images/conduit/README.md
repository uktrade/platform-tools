# Conduit Images

These images are designed to emulate most of the functionality from
[alphagov/paas-cf-conduit](https://github.com/alphagov/paas-cf-conduit)
working with the `platform-helper conduit` command.

Each image is built and pushed to the public ECR repository
[uktrade/tunnel](https://gallery.ecr.aws/uktrade/tunnel) when changes
are merged to the main branch of this repository. They are given a
Docker tag specific to the addon they allow access to.

## Supported addons

- [Postgres](./postgres) - [public.ecr.aws/uktrade/tunnel:postgres](https://gallery.ecr.aws/uktrade/tunnel)
- [Redis](./redis) - [public.ecr.aws/uktrade/tunnel:redis](https://gallery.ecr.aws/uktrade/tunnel)
- [OpenSearch](./opensearch) - [public.ecr.aws/uktrade/tunnel:opensearch](https://gallery.ecr.aws/uktrade/tunnel)

## Overview

Each image is based on [`public.ecr.aws/docker/library/debian:12-slim`](https://gallery.ecr.aws/debian/debian)
and installs the required tooling to connect to the relevant addon service.
This is because many images such as the official Postgres image will start
a server when they launch, which is not desirable for a client image.

Each image directory contains documentation on how to test and manually deploy
each image. They also contain an `entrypoint.sh` and `shell-profile.sh` file.

### `entrypoint.sh`

The entrypoint is started when the task launches in ECS, it watches for
connected users and will shut down the task when no user has been connected
for 5 minutes or more.

### `shell-profile.sh`

This is the script that runs when a user connects to the conduit task.
It should set up a connection to the appropriate addon service and kick
the user out of the session when they exit the client.

The user should at no time gain access to a shell with the ability to
arbitrarily run any other commands.
