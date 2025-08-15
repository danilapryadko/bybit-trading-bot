# Multi-stage build for Python backend and React frontend
FROM node:18-alpine AS frontend-build

# Build React frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Python backend with Telegram bot
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

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy built frontend from previous stage
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Create volume for logs and data
VOLUME ["/app/data", "/app/logs"]

# Environment variables (will be overridden by Fly.io secrets)
ENV PYTHONUNBUFFERED=1
ENV LOG_FILE=/app/logs/trading_bot.log
ENV DATABASE_URL=sqlite:///data/trading_bot.db

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose ports
EXPOSE 8000 8080

# Run the application with Telegram bot
CMD ["python", "run_with_telegram.py"]