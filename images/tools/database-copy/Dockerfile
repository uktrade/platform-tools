FROM public.ecr.aws/docker/library/debian:12-slim

RUN apt-get update && \
    apt-get upgrade -y && \
    # Add repository for postgres and install 13,14,15,16,17 and 18
    apt-get install -y postgresql-common && \
    /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y && \
    apt-get install -y jq procps postgresql-client-18 postgresql-client-17 postgresql-client-16 postgresql-client-15 postgresql-client-14 postgresql-client-13 && \
    apt-get install -y apt-utils curl gnupg unzip && \
    # Start installing AWS CLI
    curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf aws && rm awscliv2.zip && \
    apt-get remove -y apt-utils gnupg unzip && \
    # Finish installing AWS CLI
    apt-get clean

COPY entrypoint.sh /entrypoint.sh
COPY clear_db.sql /clear_db.sql

ENTRYPOINT ["bash", "/entrypoint.sh"]
