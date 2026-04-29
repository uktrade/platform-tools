FROM public.ecr.aws/amazonlinux/amazonlinux:2023-minimal

ARG PLATFORM_HELPER_VERSION="15.25.0"
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

# Install dbt-platform-helper at PLATFORM_HELPER_VERSION
RUN python3.12 -m ensurepip && \
        python3.12 -m pip install dbt-platform-helper==$PLATFORM_HELPER_VERSION && \
        python3.12 -m pip install yq

CMD ["/bin/bash"]
