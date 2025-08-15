# CI/CD Pipeline Documentation

## Overview
This document describes the CI/CD pipeline setup for the Bybit Trading Bot project, including automated testing, deployment, and maintenance workflows.

## GitHub Actions Workflows

### 1. Test Pipeline (`test.yml`)
**Trigger**: On push to main/develop branches and pull requests

**Jobs**:
- **Backend Tests**: 
  - Runs Python unit tests with pytest
  - Generates code coverage reports
  - Tests all major components (auth, reports, FastAPI)
  
- **Frontend Tests**:
  - TypeScript type checking
  - Builds the React application
  - Verifies build output
  
- **Integration Tests**:
  - Tests API endpoints
  - Verifies service communication
  - Runs with Redis service container
  
- **Security Scan**:
  - Bandit security analysis
  - Dependency vulnerability checks with Safety
  
- **Docker Build**:
  - Tests Docker image build
  - Validates container functionality

### 2. Deploy Pipeline (`deploy.yml`)
**Trigger**: Push to main branch or manual workflow dispatch

**Jobs**:
- **Test**: Runs the full test suite
- **Deploy Backend**: 
  - Deploys to Fly.io (bybit-danila-bot)
  - Rolling deployment strategy
  - Health checks after deployment
  
- **Deploy Dashboard**:
  - Builds frontend with production environment variables
  - Deploys to Fly.io (bybit-danila-dashboard)
  - Smoke tests after deployment
  
- **Notify Deployment**:
  - Sends Telegram notification with deployment status
  - Creates GitHub deployment record

### 3. Scheduled Tasks (`scheduled.yml`)
**Triggers**: 
- Daily at 00:00 UTC (health check)
- Weekly on Sundays at 12:00 UTC (performance report)
- Manual dispatch for specific tasks

**Jobs**:
- **Health Check**: Daily monitoring of both services
- **Performance Report**: Weekly trading performance summary
- **Cleanup Logs**: Remove old log files (manual)
- **Backup Data**: Create and store data backups (manual)

## Required GitHub Secrets

Configure these secrets in your repository settings:

```yaml
FLY_API_TOKEN         # Fly.io API token for deployments
TELEGRAM_BOT_TOKEN    # Telegram bot token for notifications
TELEGRAM_CHAT_ID      # Your Telegram chat ID for notifications
JWT_SECRET_KEY        # Secret key for JWT authentication
ADMIN_PASSWORD        # Default admin password
```

## Local Testing

### Running Tests Locally

```bash
# Backend tests
pytest tests/test_comprehensive.py -v

# Frontend tests
cd frontend
npm test
npm run type-check

# Integration tests
python -m uvicorn fastapi_app:app --reload &
pytest tests/integration_tests.py
```

### Pre-commit Hooks

Install pre-commit hooks to run tests before committing:

```bash
pip install pre-commit
pre-commit install
```

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11
        
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=120']
```

## Deployment Process

### Automatic Deployment
1. Push changes to `main` branch
2. Tests run automatically
3. If tests pass, deployment starts
4. Backend deploys first, then frontend
5. Health checks verify deployment
6. Telegram notification sent

### Manual Deployment

```bash
# Deploy backend
flyctl deploy --app bybit-danila-bot

# Deploy frontend
cd frontend
npm run build
flyctl deploy --app bybit-danila-dashboard

# Check status
flyctl status --app bybit-danila-bot
flyctl status --app bybit-danila-dashboard
```

### Rollback Process

```bash
# List releases
flyctl releases --app bybit-danila-bot

# Rollback to previous version
flyctl deploy --app bybit-danila-bot --image <previous-image-id>
```

## Monitoring

### Health Endpoints
- Backend: https://bybit-danila-bot.fly.dev/api/v2/health
- Dashboard: https://bybit-danila-dashboard.fly.dev

### Logs

```bash
# View backend logs
flyctl logs --app bybit-danila-bot

# View dashboard logs  
flyctl logs --app bybit-danila-dashboard

# Stream logs
flyctl logs --app bybit-danila-bot --tail
```

### Metrics

Monitor in Fly.io dashboard:
- CPU usage
- Memory consumption
- Request rate
- Error rate
- Response times

## Troubleshooting

### Common Issues

1. **Deployment Fails**
   - Check GitHub Actions logs
   - Verify secrets are set correctly
   - Check Fly.io status page

2. **Tests Failing**
   - Run tests locally to debug
   - Check for missing dependencies
   - Verify environment variables

3. **Health Check Failures**
   - Check application logs
   - Verify service is running
   - Check network connectivity

### Debug Commands

```bash
# SSH into container
flyctl ssh console --app bybit-danila-bot

# Check running processes
flyctl ssh console --app bybit-danila-bot --command "ps aux"

# View environment variables
flyctl ssh console --app bybit-danila-bot --command "env"

# Check disk usage
flyctl ssh console --app bybit-danila-bot --command "df -h"
```

## Security Best Practices

1. **Secrets Management**
   - Never commit secrets to repository
   - Use GitHub Secrets for sensitive data
   - Rotate tokens regularly

2. **Dependency Updates**
   - Dependabot configured for weekly updates
   - Review and test updates before merging
   - Monitor security advisories

3. **Access Control**
   - Limit deployment permissions
   - Use branch protection rules
   - Require PR reviews for main branch

## Performance Optimization

1. **Build Caching**
   - Docker layer caching enabled
   - NPM cache for frontend builds
   - Pip cache for Python dependencies

2. **Parallel Jobs**
   - Tests run in parallel
   - Independent deployments
   - Optimized workflow dependencies

3. **Resource Limits**
   - Appropriate Fly.io instance sizes
   - Memory limits configured
   - Auto-scaling rules set

## Maintenance

### Weekly Tasks
- Review Dependabot PRs
- Check performance metrics
- Review error logs

### Monthly Tasks  
- Update dependencies
- Review and optimize workflows
- Backup configuration audit

### Quarterly Tasks
- Security audit
- Performance review
- Cost optimization review

## Contact

For issues or questions about the CI/CD pipeline:
- Create an issue in the repository
- Contact the maintainer via Telegram
- Check the troubleshooting guide above