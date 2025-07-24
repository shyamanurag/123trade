# MINIMAL TEST DEPLOYMENT - BASIC FUNCTIONALITY ONLY
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Install minimal Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy core application
COPY app.py ./
COPY src/ ./src/
COPY config/ ./config/

# Setup user and permissions
RUN useradd app && \
    mkdir -p logs && \
    chown -R app:app /app

USER app

EXPOSE 8000

CMD ["python", "app.py"]
