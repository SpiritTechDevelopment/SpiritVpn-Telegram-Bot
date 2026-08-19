
#   docker build -t spiritvpn-bot:<тег> .

FROM python:3.12-slim AS build

ENV POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PIP_NO_CACHE_DIR=1

RUN pip install --no-cache-dir poetry==2.2.1

WORKDIR /src

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root

COPY src ./src
COPY proto ./proto


FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --system --uid 10001 --create-home --shell /usr/sbin/nologin spiritvpn-bot

COPY --from=build --chown=spiritvpn-bot:spiritvpn-bot /src/.venv /app/.venv
COPY --from=build --chown=spiritvpn-bot:spiritvpn-bot /src/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src"

WORKDIR /app

USER spiritvpn-bot

ENTRYPOINT ["python", "-m", "spiritvpn_bot"]
