# GraphQL API Microservice
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and main file
COPY requirements.txt .
COPY main.py .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared code from parent directory
COPY ../../bybit_connector.py .
COPY ../../config.py .
COPY ../../database ./database

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV SERVICE_TYPE=graphql-api

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run GraphQL API
CMD ["python", "main.py"]