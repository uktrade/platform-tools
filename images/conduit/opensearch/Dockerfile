FROM public.ecr.aws/opensearchproject/opensearch:latest
ARG OPENSEARCH_CLI_VERSION=1.1.0
USER root
RUN yum install -y jq procps unzip

# Shell and entrypoint
COPY shell-profile.sh /usr/share/opensearch/.bashrc
COPY entrypoint.sh /entrypoint.sh

# Opensearch CLI
ADD https://artifacts.opensearch.org/opensearch-clients/opensearch-cli/opensearch-cli-${OPENSEARCH_CLI_VERSION}-linux-arm64.zip /opensearch-cli.zip
RUN cd /usr/share/opensearch/ && unzip /opensearch-cli.zip

USER opensearch

ENTRYPOINT ["bash", "/entrypoint.sh"]
