# nginx-dbt-platform

Load balancing with healthcheck used to reverse proxy to instances outside of AWS infrastructure.

Currently published manually. See https://uktrade.atlassian.net/browse/DBTP-752.

## Configuration

Configuration is applied via environment variables exposed to the container at run time.

- `ALLOW_WEBSOCKETS` - allow the server to proxy websocket connections (currently not in combination with ip-filter).
- `PRIV_PATH_LIST` - a list of paths that will be routed via the ip filter container.
- `PUB_PATH_LIST` - a list of paths that will be routed directly to the application container.
- `PRIV_HOST_LIST` - a list of domain names that will be routed via the ip filter container.
- `PUB_HOST_LIST` - a list of domain names that will be routed directly to the application container.

## Building the Image

If building on an ARM mac, the image will build but will fail to deploy to Fargate with the following error:
exec /usr/bin/dumb-init: exec format error

Instead, build the image via the below command, to build for the linux/amd64 platform.

`DOCKER_DEFAULT_PLATFORM=linux/amd64 docker build --tag public.ecr.aws/uktrade/nginx-dbt-platform:<tag> .`
