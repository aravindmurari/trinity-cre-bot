FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model at build time so startup doesn't fetch from HuggingFace
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

COPY backend/ ./backend/
COPY knowledge/ ./knowledge/

WORKDIR /app/backend
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
