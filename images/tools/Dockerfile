FROM public.ecr.aws/docker/library/debian:12-slim

RUN apt-get update && \
    apt-get upgrade -y && \
    # Add repository for postgres version 16
    apt-get install -y postgresql-common && \
    /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y && \
    apt-get install -y jq procps postgresql-client-16 && \
    # Start installing AWS CLI
    curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf aws && rm awscliv2.zip && \
    apt-get remove -y apt-utils gnupg unzip && \
    # Finish installing AWS CLI
    apt-get clean

COPY shell-profile.sh /root/.bashrc
COPY entrypoint.sh /entrypoint.sh

ENTRYPOINT ["bash", "/entrypoint.sh"]
