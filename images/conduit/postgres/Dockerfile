FROM public.ecr.aws/docker/library/debian:13-slim

RUN apt-get update && \
    apt-get upgrade -y && \
    # Add repository for postgres version 17
    apt-get install -y postgresql-common && \
    /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y && \
    apt-get install -y jq procps postgresql-client-17 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY shell-profile.sh /root/.bashrc
COPY entrypoint.sh /entrypoint.sh

ENTRYPOINT ["bash", "/entrypoint.sh"]
