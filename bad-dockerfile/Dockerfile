# Bad practice: floating tag makes builds non-reproducible
FROM ubuntu:latest

# Bad practice: explicitly running everything as root
USER root

# Bad practice: storing secrets directly in the image
ENV DATABASE_PASSWORD="super-secret-password"
ENV API_KEY="12345-insecure-api-key"

# Bad practice: disabling interactive prompts globally
ENV DEBIAN_FRONTEND=noninteractive

# Bad practice:
# - apt-get update and install are separated
# - package versions are not pinned
# - unnecessary packages are installed
# - recommended packages are included
# - apt cache is not removed
RUN apt-get update

RUN apt-get install -y \
    curl \
    wget \
    git \
    vim \
    sudo \
    openssh-server \
    python3 \
    python3-pip

# Bad practice: copying the entire build context
# This may include .git, secrets, local files, and credentials
COPY . /

# Bad practice: overly permissive filesystem permissions
RUN chmod -R 777 /

# Bad practice: installing an unpinned dependency as root
RUN pip3 install flask --break-system-packages

# Bad practice: downloading and executing an unverified remote script
RUN curl -s http://example.com/install.sh | bash

# Bad practice: exposing unnecessary and sensitive ports
EXPOSE 22
EXPOSE 80
EXPOSE 5000
EXPOSE 3306

# Bad practice: no dedicated working directory
WORKDIR /

# Bad practice: undocumented anonymous volume
VOLUME ["/data"]

# Bad practice: no HEALTHCHECK
# Bad practice: application continues to run as root
# Bad practice: shell-form CMD handles signals poorly
CMD python3 /app.py