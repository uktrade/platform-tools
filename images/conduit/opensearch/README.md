# Opensearch Conduit

## Publishing manually

Requires:

- [`docker`](https://www.docker.com)
- [`aws` CLI](https://aws.amazon.com/cli/)

From this image directory:

1. `aws sso login`
2. `aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws/uktrade`
3. `docker build -t public.ecr.aws/uktrade/tunnel:opensearch .`
4. `docker tag public.ecr.aws/uktrade/tunnel:opensearch public.ecr.aws/uktrade/tunnel:opensearch-$(git rev-parse --short HEAD)`
5. `docker push public.ecr.aws/uktrade/tunnel:opensearch`
6. `docker push public.ecr.aws/uktrade/tunnel:opensearch-$(git rev-parse --short HEAD)`
7. `docker logout public.ecr.aws/uktrade`

## Testing locally

Requires:

- [`docker`](https://www.docker.com)
- [`docker-compose`](https://docs.docker.com/compose/)

Steps:

1. `docker-compose up` to bring up the client and cluster.
2. `docker-compose exec client bash` to connect to the cluster.
3. You will now be in a `opensearch-cli` session, run `curl get --path /_cat/health` to check current cluster health.
4. Enter `ctrl+c` to exit.
5. Note that the client container will now show a shutdown countdown in `docker-compose` logs every 60 seconds.
