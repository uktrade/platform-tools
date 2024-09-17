nginx-loadbalancer

Load balancing with healthcheck used to reverse proxy to instances outside of AWS infrastructure.

Currently published manually. See https://uktrade.atlassian.net/browse/DBTP-752.

### Building the Image

If building on a ARM mac, the image will build but will fail to deploy to Fargate with the following error:
exec /usr/bin/dumb-init: exec format error

Instead, build the image via the below command, to build for the linux/amd64 platform.

`DOCKER_DEFAULT_PLATFORM=linux/amd64 docker build --tag public.ecr.aws/uktrade/nginx-dbt-platform:<tag> .`