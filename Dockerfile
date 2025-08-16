# Python backend with Telegram bot and GraphQL API
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

# Run only GraphQL API server with REAL Bybit connection (no Telegram bot conflicts)
CMD ["python", "start_api_only.py"]