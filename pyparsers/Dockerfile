FROM python:3.11-slim
WORKDIR /app
COPY . .
# Install dependencies
RUN pip install --upgrade pip \
    && if [ -f pyproject.toml ]; then pip install .; fi \
    && if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
EXPOSE 5000
CMD ["python", "api_server.py"] 