# nginx-dbt-platform

Load balancing with healthcheck used to reverse proxy to instances outside of AWS infrastructure.

## Build and publish nginx-dbt-platform

Until [DBTP-752 Automate the build of DBT nginx-dbt-platform image](https://uktrade.atlassian.net/browse/DBTP-752) is done, `nginx-dbt-platform` is built and published manually.

Build the image:

```shell
# From images/nginx-dbt-platform...

DOCKER_DEFAULT_PLATFORM=linux/amd64 docker build --tag public.ecr.aws/uktrade/nginx-dbt-platform:<image_tag> .

```

Publish the image:

```shell
docker push public.ecr.aws/uktrade/nginx-dbt-platform:<image_tag>
```
