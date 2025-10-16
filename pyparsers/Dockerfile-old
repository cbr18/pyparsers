FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir fastapi uvicorn[standard] requests aiohttp beautifulsoup4 selenium playwright pydantic googletrans==4.0.2

# Install Chromium browser and chromedriver with needed system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium chromium-driver ca-certificates fonts-liberation wget \
    libasound2 libatk1.0-0 libatk-bridge2.0-0 libc6 libxcb1 libx11-6 \
    libnss3 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 \
    libxrandr2 libgbm1 libglib2.0-0 libgtk-3-0 libpango-1.0-0 libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

COPY . .

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "5000", "--reload", "--timeout-keep-alive", "3600"]