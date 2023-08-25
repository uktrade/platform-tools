FROM public.ecr.aws/docker/library/debian:12-slim

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y jq procps lsb-release ca-certificates curl gpg && \
    update-ca-certificates && \
    apt-get clean

RUN curl -fsSL https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
RUN echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/redis.list
RUN apt-get update && apt-get install -y redis && apt-get clean

COPY shell-profile.sh /root/.bashrc
COPY entrypoint.sh /entrypoint.sh

ENTRYPOINT ["bash", "/entrypoint.sh"]
