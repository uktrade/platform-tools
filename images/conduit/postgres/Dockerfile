FROM public.ecr.aws/docker/library/debian:12-slim

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y jq procps postgresql-client && \
    apt-get clean

COPY shell-profile.sh /root/.bashrc
COPY entrypoint.sh /entrypoint.sh

ENTRYPOINT ["bash", "/entrypoint.sh"]
