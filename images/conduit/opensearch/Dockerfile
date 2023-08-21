FROM public.ecr.aws/docker/library/debian:12-slim
ARG OPENSEARCH_CLI_VERSION=1.1.0
RUN apt-get update && apt-get install -y jq gawk procps unzip bash && apt-get clean

# Shell and entrypoint
COPY shell-profile.sh /root/.bashrc
COPY entrypoint.sh /entrypoint.sh

# Opensearch CLI
ADD https://artifacts.opensearch.org/opensearch-clients/opensearch-cli/opensearch-cli-${OPENSEARCH_CLI_VERSION}-linux-arm64.zip /opensearch-cli.zip
RUN cd /root && unzip /opensearch-cli.zip

ENTRYPOINT ["bash", "/entrypoint.sh"]
