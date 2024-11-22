FROM public.ecr.aws/docker/library/postgres:16

RUN apt-get update && apt upgrade -y
RUN apt-get install -y curl zip jq
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install

COPY entrypoint.sh /entrypoint.sh
COPY clear_db.sql /clear_db.sql

ENTRYPOINT ["bash", "/entrypoint.sh"]
