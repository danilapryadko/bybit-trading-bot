# 🔐 SECRETS & CREDENTIALS MANAGEMENT

## ⚠️ IMPORTANT SECURITY NOTICE
This file documents WHERE secrets are stored, NOT the actual secrets.
NEVER commit actual secrets to the repository!

---

## 📍 SECRET LOCATIONS

### 1. GitHub Secrets (for CI/CD)
Location: GitHub Repository Settings → Secrets → Actions
URL: https://github.com/danilapryadko/bbBot/settings/secrets/actions

**Required Secrets:**
- ✅ `FLY_API_TOKEN` - Fly.io deployment token (Set on Aug 15, 2024)

**Optional Secrets:**
- ⏳ `TEST_API_KEY` - Bybit Testnet API Key (for automated testing)
- ⏳ `TEST_API_SECRET` - Bybit Testnet API Secret 
- ⏳ `TELEGRAM_BOT_TOKEN` - For notifications
- ⏳ `TELEGRAM_CHAT_ID` - For notifications

**To view secrets:**
```bash
gh secret list --repo danilapryadko/bbBot
```

**To add a secret:**
```bash
gh secret set SECRET_NAME --repo danilapryadko/bbBot
```

---

## 2. Fly.io Secrets (Production Environment)
Location: Fly.io Application Environment
App Name: bybit-trading-bot

**Current Secrets:**
- ✅ `API_KEY` - Bybit API Key
- ✅ `API_SECRET` - Bybit API Secret
- ✅ `BYBIT_TESTNET` - true/false
- ✅ `SYMBOL` - Trading symbol
- ✅ `LEVERAGE` - Trading leverage
- ✅ `POSITION_SIZE` - Position size
- ✅ `STOP_LOSS_PERCENT` - Stop loss percentage
- ✅ `TAKE_PROFIT_PERCENT` - Take profit percentage
- ✅ `DATABASE_URL` - PostgreSQL connection (auto-set by Fly.io)

**To view secrets:**
```bash
fly secrets list --app bybit-trading-bot
```

**To update a secret:**
```bash
fly secrets set SECRET_NAME=value --app bybit-trading-bot
```

**To update multiple secrets:**
```bash
fly secrets set \
  API_KEY=xxx \
  API_SECRET=yyy \
  --app bybit-trading-bot
```

---

## 3. Local Development (.env file)
Location: Project root (`.env`)
Status: ⚠️ EXCLUDED from Git via .gitignore

**Template:** `.env.example`
```env
# Copy .env.example to .env and fill in your values
cp .env.example .env
```

**Never commit .env file!**
The `.env` file is listed in `.gitignore` to prevent accidental commits.

---

## 4. Database Credentials
**PostgreSQL on Fly.io:**
- Automatically managed by Fly.io
- Connection string in `DATABASE_URL` environment variable
- No manual configuration needed

**Local PostgreSQL:**
- Default: `postgresql://trader:password@localhost:5432/trading_bot`
- Configure in docker-compose.yml

---

## 🔄 SECRET ROTATION PROCEDURES

### Rotating Bybit API Keys:
1. Generate new keys on Bybit
2. Update in Fly.io: `fly secrets set API_KEY=new_key API_SECRET=new_secret`
3. Verify deployment: `fly status`
4. Delete old keys from Bybit

### Rotating Fly.io Token:
1. Generate new token: `fly auth token`
2. Update in GitHub: `gh secret set FLY_API_TOKEN`
3. Verify CI/CD pipeline still works

---

## 🛡️ SECURITY BEST PRACTICES

1. **Never hardcode secrets** in source code
2. **Use environment variables** for all sensitive data
3. **Rotate keys regularly** (every 90 days minimum)
4. **Use different keys** for dev/staging/production
5. **Enable 2FA** on all accounts (GitHub, Fly.io, Bybit)
6. **Audit access logs** regularly
7. **Use read-only keys** where possible

---

## 🚨 INCIDENT RESPONSE

If secrets are exposed:
1. **Immediately rotate** all affected credentials
2. **Check logs** for unauthorized access
3. **Update secrets** in all environments
4. **Notify team** if applicable
5. **Document incident** for future reference

---

## 📝 CHECKLIST FOR NEW DEVELOPERS

- [ ] Never commit .env file
- [ ] Use .env.example as template
- [ ] Get Fly.io access from admin
- [ ] Set up GitHub secrets for your fork
- [ ] Use testnet keys for development
- [ ] Enable 2FA on all accounts
- [ ] Read security best practices

---

## 🔧 USEFUL COMMANDS

```bash
# GitHub Secrets
gh secret list --repo danilapryadko/bbBot
gh secret set SECRET_NAME --repo danilapryadko/bbBot

# Fly.io Secrets
fly secrets list --app bybit-trading-bot
fly secrets set KEY=value --app bybit-trading-bot
fly ssh console --app bybit-trading-bot

# Local Environment
cp .env.example .env
source .env

# Check what's excluded from Git
git status --ignored
```

---

## 📞 EMERGENCY CONTACTS

**If secrets are compromised:**
1. Rotate Bybit API keys immediately
2. Contact: danilapryadko@icloud.com
3. Check GitHub audit log
4. Review Fly.io access logs

---

**Last Updated:** August 15, 2024
**Maintained by:** Danila Pryadko
