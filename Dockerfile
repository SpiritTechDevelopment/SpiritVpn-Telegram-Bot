
#   docker build -t spiritvpn-bot:<тег> .

FROM python:3.12-slim AS build

ENV POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PIP_NO_CACHE_DIR=1

RUN pip install --no-cache-dir poetry==2.2.1

# Собирается сразу по конечному пути, а не в /src. Poetry прописывает
# консольным скриптам абсолютный шебанг на интерпретатор своего venv, и при
# сборке в /src с последующим копированием в /app он указывает на
# /src/.venv/bin/python, которого в финальном образе нет. Скрипт при этом
# существует, а exec отвечает `no such file or directory` — про интерпретатор,
# а не про скрипт. `python -m ...` это не задевало, поэтому сам бот работал, а
# `alembic` из того же образа падал.
WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root

COPY src ./src
COPY proto ./proto
# Миграции едут в образе вместе с кодом, который их ожидает: инфраструктура
# гоняет `alembic upgrade head` из этого же образа, поэтому схема и код всегда
# приезжают одной парой.
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini


FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --system --uid 10001 --create-home --shell /usr/sbin/nologin spiritvpn-bot

COPY --from=build --chown=spiritvpn-bot:spiritvpn-bot /app/.venv /app/.venv
COPY --from=build --chown=spiritvpn-bot:spiritvpn-bot /app/src /app/src
COPY --from=build --chown=spiritvpn-bot:spiritvpn-bot /app/migrations /app/migrations
COPY --from=build --chown=spiritvpn-bot:spiritvpn-bot /app/alembic.ini /app/alembic.ini

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src"

WORKDIR /app

USER spiritvpn-bot

ENTRYPOINT ["python", "-m", "spiritvpn_bot"]
