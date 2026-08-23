FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies (with BuildKit cache for faster rebuilds)
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu --default-timeout=100
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt --default-timeout=100

# Copy application code
COPY . .
RUN chmod +x /app/backend-entrypoint.sh

# Run with hot-reload for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
