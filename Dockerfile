# =============================================================================
# ENHANCED MULTI-STAGE DOCKERFILE FOR CRYPTO TRADING SYSTEM
# =============================================================================

# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_ENV=production
ARG BUILD_DATE
ARG VERSION=4.0.1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt requirements-test.txt ./

# Create virtual environment and install dependencies
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Upgrade pip and install dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set labels for better container management
LABEL maintainer="trading-system@company.com"
LABEL version="${VERSION}"
LABEL build_date="${BUILD_DATE}"
LABEL description="Enhanced Crypto Trading System"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONHASHSEED=random
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r trading && useradd -r -g trading -s /bin/bash trading

# Create directories with proper permissions
RUN mkdir -p /app/logs /app/data /app/backups /app/config && \
    chown -R trading:trading /app

# Copy virtual environment from builder
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application files with proper ownership
COPY --chown=trading:trading app.py ./
COPY --chown=trading:trading main.py ./

# Copy source code structure
COPY --chown=trading:trading src/ src/
COPY --chown=trading:trading config/ config/
COPY --chown=trading:trading database/ database/

# Copy essential configuration files
COPY --chown=trading:trading *.env* ./
COPY --chown=trading:trading *.yaml ./
COPY --chown=trading:trading *.yml ./

# Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Health check function\n\
health_check() {\n\
    curl -f http://localhost:8000/api/health/liveness || exit 1\n\
}\n\
\n\
# Start application\n\
echo "Starting Crypto Trading System v${VERSION}..."\n\
echo "Environment: ${ENVIRONMENT:-production}"\n\
echo "Trading Mode: ${TRADING_MODE:-free-tier}"\n\
\n\
# Run database migrations if needed\n\
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then\n\
    echo "Running database migrations..."\n\
    python -c "from src.database.migrations import run_migrations; run_migrations()" || echo "Migration failed or not available"\n\
fi\n\
\n\
# Start the application\n\
exec python app.py\n\
' > /app/start.sh && chmod +x /app/start.sh

# Switch to non-root user
USER trading

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/health/liveness || exit 1

# Expose port
EXPOSE 8000

# Start application
CMD ["/app/start.sh"]

# =============================================================================
# DEVELOPMENT STAGE (for local development)
# =============================================================================
FROM production as development

USER root

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Install test dependencies
COPY --chown=trading:trading requirements-test.txt ./
RUN /venv/bin/pip install -r requirements-test.txt

# Install development tools
RUN /venv/bin/pip install \
    watchdog[watchmedo] \
    ipython \
    jupyter

USER trading

# Override command for development
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
