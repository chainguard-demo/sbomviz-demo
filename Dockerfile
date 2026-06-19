# Build stage — CSS assets (shell + npm)
FROM cgr.dev/chainguard-private/node:22-dev@sha256:1d9c35f11ed2d95b2c1e99bb40e034b488b4e7b78ed203577f9c0d1c95a7b929 AS css-builder

WORKDIR /app

COPY --chown=65532:65532 package.json package-lock.json ./
COPY --chown=65532:65532 scripts/configure-npm-libraries.sh ./scripts/configure-npm-libraries.sh

ARG CHAINGUARD_JAVASCRIPT_IDENTITY_ID
ARG CHAINGUARD_JAVASCRIPT_TOKEN
ENV CHAINGUARD_JAVASCRIPT_IDENTITY_ID=$CHAINGUARD_JAVASCRIPT_IDENTITY_ID
ENV CHAINGUARD_JAVASCRIPT_TOKEN=$CHAINGUARD_JAVASCRIPT_TOKEN

RUN chmod +x ./scripts/configure-npm-libraries.sh \
    && ./scripts/configure-npm-libraries.sh \
    && npm ci

COPY --chown=65532:65532 static/src ./static/src
COPY --chown=65532:65532 templates ./templates
RUN npm run build:css

# Build stage — Python dependencies (shell + pip)
FROM cgr.dev/chainguard-private/python:latest-dev@sha256:1a743d03c5195175bb5a0614196d24a72d47efc67e265b56a57e4763688a1038 AS python-builder

WORKDIR /app

USER root
RUN mkdir -p /opt/deps && chown 65532:65532 /opt/deps
USER nonroot

ARG CHAINGUARD_PYTHON_IDENTITY_ID
ARG CHAINGUARD_PYTHON_TOKEN

COPY --chown=65532:65532 requirements.txt /app/requirements.txt
RUN if [ -z "$CHAINGUARD_PYTHON_IDENTITY_ID" ] || [ -z "$CHAINGUARD_PYTHON_TOKEN" ]; then \
      echo "Missing Chainguard auth env vars for build."; \
      echo "Set CHAINGUARD_PYTHON_IDENTITY_ID and CHAINGUARD_PYTHON_TOKEN before docker compose build/up."; \
      exit 1; \
    fi \
    && ENCODED_CREDS="$(python -c 'import os, urllib.parse; print("{}:{}".format(urllib.parse.quote(os.environ["CHAINGUARD_PYTHON_IDENTITY_ID"], safe=""), urllib.parse.quote(os.environ["CHAINGUARD_PYTHON_TOKEN"], safe="")) )')" \
    && PIP_INDEX_URL="https://${ENCODED_CREDS}@libraries.cgr.dev/python/simple/" \
      python -m pip install --no-cache-dir \
        -r /app/requirements.txt \
        --target /opt/deps

# Runtime stage — minimal, distroless, digest-pinned
FROM cgr.dev/chainguard-private/python:latest@sha256:9dc292658c17d7f49832f76fb593a8dc39c8d6d8fe727dac25a370547df3079f

WORKDIR /app

ENV PYTHONPATH=/opt/deps

COPY --from=python-builder /opt/deps /opt/deps
COPY --chown=nonroot:nonroot . /app
COPY --from=css-builder --chown=nonroot:nonroot /app/static/styles.css /app/static/styles.css

EXPOSE 8000

CMD ["app.py"]
