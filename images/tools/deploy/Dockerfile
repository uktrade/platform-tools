FROM public.ecr.aws/amazonlinux/amazonlinux:2023-minimal

ARG PLATFORM_HELPER_VERSION="15.29.0" # x-release-please-version
ARG TERRAFORM_VERSION="1.13.0"
ARG PYTHON_VERSION="3.12"

# Install DNF packages required for build and Python at PYTHON_VERSION
RUN dnf install -y \
        python$PYTHON_VERSION \
        unzip \
        awscli \
        jq && \
        dnf clean all

# Install Terraform at TERRAFORM_VERSION
RUN curl -s -qL -o terraform_install.zip https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
        unzip terraform_install.zip && \
        mv terraform /usr/local/bin/ && \
        rm -f terraform_install.zip

# Install dbt-platform-helper at PLATFORM_HELPER_VERSION (released version)
RUN python${PYTHON_VERSION} -m ensurepip && \
        python${PYTHON_VERSION} -m pip install --no-cache-dir \
                dbt-platform-helper==$PLATFORM_HELPER_VERSION \
                yq

# # Install local dbt-platform-helper
# COPY . /tmp/platform-tools

# RUN python${PYTHON_VERSION} -m ensurepip && \
#         python${PYTHON_VERSION} -m pip install --no-cache-dir \
#                 /tmp/platform-tools \
#                 yq && \
#         rm -rf /tmp/platform-tools

# COPY ../../../terraform/ecs-service ./terraform-modules/ecs-service
# COPY ../../../terraform/version-tracker ./terraform-modules/version-tracker

CMD ["/bin/bash"]
