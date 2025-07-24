# ULTRA-MINIMAL SINGLE-STAGE BUILD FOR DIGITALOCEAN
FROM python:3.11-slim

# Essential environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Install only absolute essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && \
    rm -rf /var/lib/apt/lists/* && \
    useradd --create-home --no-log-init app

# Set working directory
WORKDIR /app

# Copy and install requirements first
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy only essential application files
COPY app.py .
COPY src/ ./src/
COPY config/ ./config/

# Create directories and set permissions in one layer
RUN mkdir -p logs config data backups frontend/dist && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Simple command
CMD ["python", "app.py"]
