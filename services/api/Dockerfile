# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm AS dependencies

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv==0.8.13

COPY services/api/pyproject.toml services/api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --gid 10001 gradmatch \
    && useradd --uid 10001 --gid gradmatch --create-home --shell /usr/sbin/nologin gradmatch \
    && mkdir /app/staticfiles \
    && chown -R gradmatch:gradmatch /app

COPY --from=dependencies --chown=gradmatch:gradmatch /app/.venv /app/.venv
COPY --chown=gradmatch:gradmatch services/api/manage.py ./manage.py
COPY --chown=gradmatch:gradmatch services/api/src ./src

USER gradmatch

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=6 \
  CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/api/v1/health/live', timeout=3).read()"

CMD ["uvicorn", "gradmatch.config.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
