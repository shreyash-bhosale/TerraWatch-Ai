FROM python:3.13-slim

WORKDIR /app

# Install curl for container healthcheck and libexpat1 required by rasterio wheel on Debian slim
RUN apt-get update && apt-get install -y --no-install-recommends curl libexpat1 && rm -rf /var/lib/apt/lists/*

# Install pinned Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source
COPY backend ./backend
RUN mkdir -p /app/data/synthetic /app/data/jobs /app/data/outputs /app/data/local

ENV PYTHONPATH=/app/backend
ENV PROVIDER=mock
ENV DATA_DIR=/app/data
ENV LOCAL_DATA_DIR=/app/data/local
ENV PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Regenerate deterministic synthetic fixtures on container start, then launch FastAPI
CMD ["sh", "-c", "python backend/scripts/make_synthetic.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

