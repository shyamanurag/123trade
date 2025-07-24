# =====================================================
# MINIMAL DOCKERFILE FOR FAST DIGITALOCEAN DEPLOYMENT
# =====================================================

# Frontend build stage - keep minimal
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --only=production
COPY frontend/ ./
RUN npm run build

# =====================================================
# MINIMAL PYTHON BACKEND - OPTIMIZED FOR SPEED
# =====================================================
FROM python:3.11-slim

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# MINIMAL system dependencies - only what's absolutely required
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN useradd --create-home --no-log-init --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy and install Python dependencies FIRST (for better caching)
COPY requirements.txt .

# Install Python packages using pre-built wheels (much faster)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create required directories and set permissions
RUN mkdir -p logs config data backups && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Simple health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Single command - no fallbacks
CMD ["python", "app.py"]
