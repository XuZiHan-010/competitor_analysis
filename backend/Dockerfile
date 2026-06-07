FROM python:3.11-slim

WORKDIR /app

# Playwright needs curl + system libs; --with-deps handles the rest
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir -e .

# Install Chromium and its system-level dependencies inside the image
RUN playwright install chromium --with-deps

EXPOSE 8000

# Run DB migrations then start server; Railway injects $PORT
CMD alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
