FROM public.ecr.aws/amazonlinux/amazonlinux:2023-minimal

ARG PLATFORM_HELPER_VERSION
ARG PLATFORM_HELPER_VERSION_OVERRIDE
ARG TERRAFORM_VERSION="1.15.7"
ARG PYTHON_VERSION="3.12"

RUN dnf install -y \
        python${PYTHON_VERSION} \
        unzip \
    && dnf clean all \
    && rm -rf /var/cache/dnf

RUN curl -s -qL -o terraform_install.zip https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
        unzip terraform_install.zip && \
        mv terraform /usr/local/bin/ && \
        rm -f terraform_install.zip

RUN python${PYTHON_VERSION} -m ensurepip \
    && python${PYTHON_VERSION} -m pip install --upgrade pip

# BuildKit bind mount - makes the local repo available during this RUN step without copying it into the image or leaving it in the final layers
RUN --mount=type=bind,source=.,target=/tmp/platform-tools,readonly \
    if [ -n "${PLATFORM_HELPER_VERSION_OVERRIDE}" ] && [ -n "${PLATFORM_HELPER_VERSION}" ]; then \
        echo "Only one of PLATFORM_HELPER_VERSION or PLATFORM_HELPER_VERSION_OVERRIDE may be set"; \
        exit 1; \
    elif [ -n "${PLATFORM_HELPER_VERSION_OVERRIDE}" ]; then \
        echo "Installing Platform Helper from local platform-tools repo"; \
        python${PYTHON_VERSION} -m pip install --no-cache-dir /tmp/platform-tools; \
    elif [ -n "${PLATFORM_HELPER_VERSION}" ]; then \
        echo "Installing Platform Helper from PyPI: ${PLATFORM_HELPER_VERSION}"; \
        python${PYTHON_VERSION} -m pip install --no-cache-dir "dbt-platform-helper==${PLATFORM_HELPER_VERSION}"; \
    else \
        echo "Only one of PLATFORM_HELPER_VERSION or PLATFORM_HELPER_VERSION_OVERRIDE must be set"; \
        exit 1; \
    fi

CMD ["/bin/bash"]
