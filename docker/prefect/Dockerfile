FROM python:3.12-slim

ARG CIRCE_EXTRAS="prefect,ibis-postgres,ibis-databricks"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PREFECT_HOME=/tmp/prefect \
    HOME=/home/circe

WORKDIR /app

# Install the project and the runner extras.  Prefect is optional for library
# users, but this image is the Prefect deployment image.
COPY pyproject.toml README.md MANIFEST.in ./
COPY circe ./circe
RUN python -m pip install --upgrade pip \
    && python -m pip install ".[${CIRCE_EXTRAS}]" \
    && useradd --create-home --uid 10001 circe \
    && mkdir -p /data /home/circe \
    && chown -R circe:circe /app /data /home/circe

COPY docker/prefect/entrypoint.sh /usr/local/bin/circe-runner
RUN chmod 0755 /usr/local/bin/circe-runner

USER circe

ENTRYPOINT ["/usr/local/bin/circe-runner"]
CMD ["--payload", "/payload.json"]
