# Stage 1: Build the frontend
FROM node:18.19.0-slim AS frontend-builder

WORKDIR /frontend

# Copy frontend package files
COPY src/frontend/package*.json ./

# Install all dependencies including dev dependencies
RUN npm ci

# Copy frontend source
COPY src/frontend/ ./

# Build frontend with environment variables
ARG VITE_API_URL
ARG VITE_WS_URL
ARG VITE_APP_NAME
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL
ENV VITE_APP_NAME=$VITE_APP_NAME

# Build frontend
RUN npm run build

# Stage 2: Python application
FROM python:3.11.2-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy built frontend from frontend-builder stage
COPY --from=frontend-builder /frontend/dist ./static

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["gunicorn", "main:app", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]