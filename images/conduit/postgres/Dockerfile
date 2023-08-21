# Pull latest PostgreSQL Docker image
FROM public.ecr.aws/docker/library/postgres:latest

RUN apt-get update && apt-get install -y jq procps && apt-get clean

COPY shell-profile.sh /root/.bashrc
COPY entrypoint.sh /entrypoint.sh

ENTRYPOINT ["bash", "/entrypoint.sh"]
