FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8765 \
    # Defaults match docker-compose volume mount points
    VAULT_ROOT=/vault \
    HERMES_HOME=/hermes \
    STUDY_DATA_ROOT=/hermes/home \
    STUDY_DB_PATH=/hermes/home/study-system.sqlite3 \
    CHROMA_PATH=/hermes/mem0/chroma-jina \
    CLIPROXY_KEY_FILE=/secrets/cliproxy/api_key \
    CLIPROXY_BASE=http://cli-proxy-api:8317/v1

# chromadb / onnxruntime need a few system libs
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py index.html ./
COPY assets ./assets

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/health')" \
  || python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/')"

CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8765"]
