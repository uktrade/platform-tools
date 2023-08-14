# Postgres Conduit

## Publishing Manually

Requires:

- `docker`
- `aws` cli

From this image directory:

1. `docker build -t public.ecr.aws/uktrade/tunnel:postgres .`
2. `docker tag public.ecr.aws/uktrade/tunnel:postgres public.ecr.aws/uktrade/tunnel:postgres-$(git rev-parse --short HEAD) .`
3. `aws sso login`
4. `aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws/uktrade`
5. `docker push public.ecr.aws/uktrade/tunnel:postgres`
6. `docker push public.ecr.aws/uktrade/tunnel:postgres-$(git rev-parse --short HEAD)`

## Testing Locally

Requires:

- `docker`
- `docker-compose`

Steps:

1. `docker-compose up` to bring up the client and database
2. `docker-compose exec client bash` to connect to the database
3. You will now be in a `psql` session, run `\list` to check available schemas
4. Enter `ctrl+d` or `\q` to exit.
5. Note that the client container has now exited in `docker-compose` logs
