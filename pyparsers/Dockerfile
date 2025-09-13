FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir fastapi uvicorn[standard] requests aiohttp beautifulsoup4 selenium playwright pydantic googletrans==4.0.2

COPY . .

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "5000", "--reload", "--timeout-keep-alive", "3600"]