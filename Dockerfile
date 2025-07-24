# ULTRA-MINIMAL DOCKERFILE - FIX SNAPSHOT FAILURE
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copy and install requirements FIRST
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ONLY essential application files (avoid large directories)
COPY app.py .

# Copy src directory structure but be selective
COPY src/__init__.py src/
COPY src/api/ src/api/
COPY src/core/ src/core/
COPY src/data/ src/data/
COPY src/edge/ src/edge/
COPY src/models/ src/models/
COPY src/config/ src/config/
COPY src/strategies/ src/strategies/

# Copy essential config files only
COPY config/*.yaml config/
COPY config/*.yml config/

# Setup user and permissions
RUN useradd app && \
    chown -R app:app /app

USER app

EXPOSE 8000

CMD ["python", "app.py"]
