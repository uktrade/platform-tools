# Opensearch Conduit

## Building locally

Requires:

- [docker](https://www.docker.com)
- [aws CLI](https://aws.amazon.com/cli/)

From this image directory:

1. `aws sso login`
2. `AWS_PROFILE=platform-tools aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws/uktrade`
3. `docker build -t public.ecr.aws/uktrade/tunnel:opensearch --platform linux/arm64 .`
4. `docker tag public.ecr.aws/uktrade/tunnel:opensearch public.ecr.aws/uktrade/tunnel:opensearch-$(git rev-parse --short HEAD)`
5. `docker push public.ecr.aws/uktrade/tunnel:opensearch-$(git rev-parse --short HEAD)`

## Testing locally

Requires:

- [docker](https://www.docker.com)
- [docker-compose](https://docs.docker.com/compose/)

Steps:

1. `docker-compose up` to bring up the client and cluster.
2. `docker-compose exec client bash` to connect to the cluster.
3. You will now be in a `opensearch-cli` session, run `curl get --path /_cat/health` to check current cluster health.
4. Enter `ctrl+c` to exit.
5. Note that the client container will now show a shutdown countdown in `docker-compose` logs every 60 seconds.

## Testing in AWS

Requires:

- [aws CLI](https://aws.amazon.com/cli/)
- [platform-helper](https://pypi.org/project/dbt-platform-helper/)

Steps:

1. Log into the `platform-sandbox` AWS account via the console
2. Find the ECS task definition called `conduit-opensearch-read-demodjango-dev-demodjango-opensearch`. Could use an environment other than `dev` too
3. Create a new revision and set the image tag in `containerDefinitions.image` as `opensearch-` follow by the output from `git rev-parse --short HEAD`
4. Run `AWS_PROFILE=platform-sandbox platform-helper conduit demodjango-opensearch --app demodjango --env dev`
5. You will now be in a `opensearch-cli` session, run `curl get --path /_cat/health` to check current cluster health
6. Enter `ctrl+c` to exit
7. Once confirmed everything works, revert the task definition image tag back to `opensearch`

## Publish manually

Requires:

- [docker](https://www.docker.com)
- [aws CLI](https://aws.amazon.com/cli/)

1. `docker push public.ecr.aws/uktrade/tunnel:opensearch`
2. `docker logout public.ecr.aws/uktrade`
