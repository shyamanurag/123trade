# Stage 1: Build the frontend
FROM node:18.19.0-slim as builder

WORKDIR /app/frontend

# Copy package files and install dependencies
COPY src/frontend/package.json src/frontend/package-lock.json* ./
RUN npm install

# Copy the rest of the frontend source code
COPY src/frontend/ ./

# Build the frontend
RUN npm run build

# Stage 2: Build the final Python application
FROM python:3.11.2-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy built frontend from the builder stage
COPY --from=builder /app/frontend/dist /app/static

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Run the application
CMD ["gunicorn", "main:app", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]