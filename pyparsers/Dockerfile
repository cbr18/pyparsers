FROM python:3.13-slim AS runtime-base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:${PATH}"

RUN set -eux; \
    . /etc/os-release; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's/Components: main/Components: main contrib non-free non-free-firmware/g' /etc/apt/sources.list.d/debian.sources; \
    else \
        echo "deb http://deb.debian.org/debian ${VERSION_CODENAME} main contrib non-free non-free-firmware" >> /etc/apt/sources.list; \
        echo "deb http://deb.debian.org/debian ${VERSION_CODENAME}-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list; \
        echo "deb http://deb.debian.org/debian-security ${VERSION_CODENAME}-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list; \
    fi; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        ca-certificates \
        fonts-liberation \
        wget \
        libasound2 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libc6 \
        libxcb1 \
        libx11-6 \
        libnss3 \
        libxcomposite1 \
        libxcursor1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libglib2.0-0 \
        libgtk-3-0 \
        libpango-1.0-0 \
        libxshmfence1; \
    groupadd --system app; \
    useradd --system --gid app --create-home --home-dir /home/app --shell /usr/sbin/nologin app; \
    mkdir -p /app /tmp/uv-cache; \
    chown -R app:app /app /home/app /tmp/uv-cache; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

FROM runtime-base AS app

COPY --chown=app:app pyproject.toml uv.lock ./

USER app

RUN UV_CACHE_DIR=/tmp/uv-cache uv sync --frozen --no-dev --no-cache && rm -rf /tmp/uv-cache

COPY --chown=app:app . .

ENV HOME=/home/app
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:5000/health || exit 1

CMD ["granian", "--interface", "asgi", "--host", "0.0.0.0", "--port", "5000", "--http1-keep-alive", "async_api_server:app"]
