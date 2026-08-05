# Redis Conduit

## Building locally

Requires:

- [docker](https://www.docker.com)
- [aws CLI](https://aws.amazon.com/cli/)

From this image directory:

1. `aws sso login`
2. `AWS_PROFILE=platform-tools aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws/uktrade`
3. `docker build -t public.ecr.aws/uktrade/tunnel:redis --platform linux/arm64 .`
4. `docker tag public.ecr.aws/uktrade/tunnel:redis public.ecr.aws/uktrade/tunnel:redis-$(git rev-parse --short HEAD)`
5. `docker push public.ecr.aws/uktrade/tunnel:redis-$(git rev-parse --short HEAD)`

## Testing locally

Requires:

- [docker](https://www.docker.com)
- [docker-compose](https://docs.docker.com/compose/)

Steps:

1. `docker-compose up` to bring up the client and database
2. `docker-compose exec client bash` to connect to the database
3. You will now be in a `redis-cli` session, run `CONFIG GET databases` to check available databases
4. Enter `ctrl+d` or `QUIT` to exit
5. Note that the client container will now show a shutdown countdown in `docker-compose` logs every 60 seconds

## Testing in AWS

Requires:

- [aws CLI](https://aws.amazon.com/cli/)
- [platform-helper](https://pypi.org/project/dbt-platform-helper/)

Steps:

1. Log into the `platform-sandbox` AWS account via the console
2. Find the ECS task definition called `conduit-redis-read-demodjango-dev-demodjango-redis`. Could use an environment other than `dev` too
3. Create a new revision and set the image tag in `containerDefinitions.image` as `redis-` follow by the output from `git rev-parse --short HEAD`
4. Run `AWS_PROFILE=platform-sandbox platform-helper conduit demodjango-redis --app demodjango --env dev`
5. You will now be in a `redis-cli` session, run `CONFIG GET databases` to check available databases
6. Enter `ctrl+d` or `QUIT` to exit
7. Once confirmed everything works, revert the task definition image tag back to `redis`

## Publish manually

Requires:

- [docker](https://www.docker.com)
- [aws CLI](https://aws.amazon.com/cli/)

1. `docker push public.ecr.aws/uktrade/tunnel:redis`
2. `docker logout public.ecr.aws/uktrade`
