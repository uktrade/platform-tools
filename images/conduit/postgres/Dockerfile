FROM public.ecr.aws/docker/library/debian:12-slim

RUN apt-get update && \
    apt-get upgrade -y && \
    # Add repository for postgres version 16
    apt-get install -y postgresql-common && \
    /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y && \
    apt-get install -y jq procps postgresql-client-16 && \
    # Start installing Cloud Foundry CLI and things for GOV.UK PaaS data migrations
    apt-get install -y apt-utils curl gnupg unzip && \
    curl -sS https://packages.cloudfoundry.org/debian/cli.cloudfoundry.org.key | gpg --dearmor > /etc/apt/trusted.gpg.d/cloudfoundry-cli.gpg && \
    echo "deb https://packages.cloudfoundry.org/debian stable main" | tee /etc/apt/sources.list.d/cloudfoundry-cli.list && \
    apt-get update && \
    apt-get install -y cf8-cli && \
    cf install-plugin -f https://github.com/alphagov/paas-cf-conduit/releases/download/v0.1.0/cf-conduit.linux.arm64 && \
    # Finish installing Cloud Foundry CLI and things for GOV.UK PaaS data migrations
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
