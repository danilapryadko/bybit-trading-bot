#!/bin/bash
# Deploy complete GraphQL API to Fly.io

echo "🚀 Deploying Complete GraphQL API to Fly.io"
echo "==========================================="

# Step 1: Copy complete API to main directory
echo "📦 Preparing deployment files..."
cp services/graphql-api/complete_graphql_api.py main.py

# Step 2: Update Procfile for Fly.io
echo "📝 Creating Procfile..."
cat > Procfile << 'EOF'
web: python main.py
EOF

# Step 3: Update fly.toml to use new API
echo "⚙️ Updating fly.toml configuration..."
cat > fly.toml << 'EOF'
app = "bybit-danila-api"
primary_region = "iad"
kill_signal = "SIGINT"
kill_timeout = 5

[build]
  builder = "paketobuildpacks/builder:base"
  buildpacks = ["gcr.io/paketo-buildpacks/python"]

[env]
  PORT = "8000"
  USE_MAINNET = "true"
  PYTHONUNBUFFERED = "1"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = false
  auto_start_machines = true
  min_machines_running = 1

  [http_service.concurrency]
    type = "connections"
    hard_limit = 25
    soft_limit = 20

[[services]]
  protocol = "tcp"
  internal_port = 8000
  
  [[services.ports]]
    port = 80
    handlers = ["http"]
    
  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

[[services]]
  protocol = "tcp"
  internal_port = 8001
  
  [[services.ports]]
    port = 8001
    handlers = ["tls", "http"]

[checks]
  [checks.health]
    grace_period = "10s"
    interval = "30s"
    method = "get"
    path = "/health"
    port = 8000
    timeout = "5s"
    type = "http"
EOF

# Step 4: Create runtime.txt for Python version
echo "🐍 Setting Python version..."
echo "python-3.11.6" > runtime.txt

# Step 5: Update requirements.txt
echo "📋 Updating requirements.txt..."
cat > requirements.txt << 'EOF'
# Core dependencies
pybit==5.6.2
python-dotenv==1.0.0
pandas==2.1.3
numpy==1.26.2

# Database
psycopg2-binary==2.9.9
sqlalchemy==2.0.23

# API Framework
fastapi==0.104.1
uvicorn==0.24.0
aiohttp==3.9.1
httpx==0.25.2
websockets==12.0

# GraphQL
ariadne==0.23.0
graphql-core==3.2.6

# CORS and middleware
starlette
python-multipart==0.0.6

# Monitoring
prometheus-client==0.19.0

# Security
PyJWT==2.8.0
EOF

# Step 6: Deploy to Fly.io
echo "🚢 Deploying to Fly.io..."
fly deploy --strategy immediate

# Step 7: Check deployment status
echo "✅ Checking deployment status..."
fly status

# Step 8: Show logs
echo "📜 Recent logs:"
fly logs --limit 50

echo ""
echo "==========================================="
echo "✅ Deployment complete!"
echo ""
echo "📊 Dashboard URL: https://bybit-danila-dashboard.fly.dev"
echo "🔌 API URL: https://bybit-danila-api.fly.dev"
echo "📡 GraphQL: https://bybit-danila-api.fly.dev/graphql"
echo "🔗 WebSocket: wss://bybit-danila-api.fly.dev/ws"
echo ""
echo "Test endpoints:"
echo "  curl https://bybit-danila-api.fly.dev/health"
echo "  curl https://bybit-danila-api.fly.dev/"
echo ""
echo "To monitor logs: fly logs -a bybit-danila-api"
echo "==========================================="