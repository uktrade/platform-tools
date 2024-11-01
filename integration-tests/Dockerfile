FROM python:3.12
RUN apt-get update && apt-get install -y curl
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /src
COPY poetry.lock ./
COPY pyproject.toml ./

RUN poetry update
COPY . ./
RUN poetry install --no-root

HEALTHCHECK --interval=5m --timeout=3s \
  CMD curl -f http://localhost/ || exit 1

CMD ["poetry", "run", "pytest"]