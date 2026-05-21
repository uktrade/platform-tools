FROM public.ecr.aws/amazonlinux/amazonlinux:2023-minimal

ARG PLATFORM_HELPER_VERSION
ARG PLATFORM_HELPER_VERSION_OVERRIDE
ARG PYTHON_VERSION="3.12"

RUN dnf install -y python${PYTHON_VERSION} \
    && dnf clean all

RUN python${PYTHON_VERSION} -m ensurepip \
    && python${PYTHON_VERSION} -m pip install --upgrade pip

RUN --mount=type=bind,source=.,target=/tmp/platform-tools,readonly \
    if [ -n "${PLATFORM_HELPER_VERSION_OVERRIDE}" ] && [ -n "${PLATFORM_HELPER_VERSION}" ]; then \
        echo "Only one of PLATFORM_HELPER_VERSION or PLATFORM_HELPER_VERSION_OVERRIDE may be set"; \
        exit 1; \
    elif [ -n "${PLATFORM_HELPER_VERSION_OVERRIDE}" ]; then \
        echo "Installing Platform Helper from local platform-tools repo"; \
        python${PYTHON_VERSION} -m pip install -no-cache-dir /tmp/platform-tools; \
    elif [ -n "${PLATFORM_HELPER_VERSION}" ]; then \
        echo "Installing Platform Helper from PyPI: ${PLATFORM_HELPER_VERSION}"; \
        python${PYTHON_VERSION} -m pip install --no-cache-dir "dbt-platform-helper==${PLATFORM_HELPER_VERSION}"; \
    else \
        echo "Only one of PLATFORM_HELPER_VERSION or PLATFORM_HELPER_VERSION_OVERRIDE must be set"; \
        exit 1; \
    fi

CMD ["/bin/bash"]
